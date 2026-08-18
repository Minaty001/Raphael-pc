"""
Background Task Engine for Raphael v3 Always-Alive Runtime.

Implements the spec's background intelligence layer:
  * Task types (Section 18) & states (Section 19)
  * Priority levels (Section 20) + priority queue (Section 43)
  * Bounded worker pool (Section 22) + multitasking (Section 23)
  * Resource budgets (Section 21) + resource-aware scheduling/throttle (Section 28/48)
  * SQLite persistence + checkpointing + retry policy (Sections 29-31)
  * Task dependency graph basics (Sections 60-61)

The engine emits live task events over the Event Bus (Section 70):
  task.created / task.started / task.progress / task.paused / task.resumed /
  task.waiting / task.completed / task.failed / task.cancelled
so the UI Task Drawer updates in real time.

Public API mirrors the spec (Section 45/46):
  BackgroundTask  -> task object (run/pause/resume/cancel)
  TaskManager      -> create/get/list/pause/resume/cancel/retry/checkpoint
"""

import asyncio
import json
import time
import uuid
import sqlite3
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable, List

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus
from raphael.core.resource_manager import get_resource_manager

logger = get_logger("runtime.tasks")


# ----------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------
class TaskType(str, Enum):
    FOREGROUND = "FOREGROUND"
    BACKGROUND = "BACKGROUND"
    SCHEDULED = "SCHEDULED"
    EVENT_TRIGGERED = "EVENT_TRIGGERED"
    RECURRING = "RECURRING"
    WAITING = "WAITING"
    PAUSED = "PAUSED"


class TaskStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"
    IDLE = "IDLE"


_PRIORITY_RANK = {
    TaskPriority.CRITICAL: 0,
    TaskPriority.HIGH: 1,
    TaskPriority.NORMAL: 2,
    TaskPriority.LOW: 3,
    TaskPriority.BACKGROUND: 4,
    TaskPriority.IDLE: 5,
}


# ----------------------------------------------------------------------
# Task definition
# ----------------------------------------------------------------------
@dataclass
class BackgroundTask:
    id: str
    name: str
    priority: str = TaskPriority.NORMAL.value
    type: str = TaskType.BACKGROUND.value
    status: str = TaskStatus.CREATED.value
    progress: float = 0.0
    coroutine: Optional[Callable[..., Awaitable[None]]] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    # resource budget (Section 21)
    max_cpu: int = 25
    max_memory_mb: int = 300
    network_required: bool = False
    gpu_required: bool = False
    estimated_duration_s: int = 0
    # retry policy (Section 31)
    max_retries: int = 2
    retry_backoff_s: float = 5.0
    retryable: bool = True
    # bookkeeping
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    checkpoint: dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    error: Optional[str] = None
    result: Optional[dict] = None
    _attempt: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("coroutine", None)
        return d


# ----------------------------------------------------------------------
# Persistence (Section 30 / 29)
# ----------------------------------------------------------------------
class TaskStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                priority TEXT,
                type TEXT,
                status TEXT,
                progress REAL,
                payload TEXT,
                retry_policy TEXT,
                resources TEXT,
                checkpoint TEXT,
                dependencies TEXT,
                created_at REAL,
                started_at REAL,
                finished_at REAL,
                error TEXT,
                result TEXT
            )
            """
        )
        self.conn.commit()

    def upsert(self, task: BackgroundTask):
        self.conn.execute(
            """INSERT OR REPLACE INTO tasks
               (id,name,priority,type,status,progress,payload,retry_policy,resources,
                checkpoint,dependencies,created_at,started_at,finished_at,error,result)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                task.id, task.name, task.priority, task.type, task.status,
                task.progress, json.dumps({"args": list(task.args), "kwargs": task.kwargs}),
                json.dumps({"max_retries": task.max_retries, "backoff": task.retry_backoff_s,
                            "retryable": task.retryable}),
                json.dumps({"max_cpu": task.max_cpu, "max_memory_mb": task.max_memory_mb,
                            "network": task.network_required, "gpu": task.gpu_required,
                            "estimated": task.estimated_duration_s}),
                json.dumps(task.checkpoint), json.dumps(task.dependencies),
                task.created_at, task.started_at, task.finished_at, task.error,
                json.dumps(task.result) if task.result else None,
            ),
        )
        self.conn.commit()

    def load_unfinished(self) -> List[dict]:
        rows = self.conn.execute(
            "SELECT * FROM tasks WHERE status NOT IN ('COMPLETED','FAILED','CANCELLED')"
        ).fetchall()
        return [dict(r) for r in rows]


# ----------------------------------------------------------------------
# Manager + worker pool (Sections 22/43/44)
# ----------------------------------------------------------------------
class TaskManager:
    def __init__(self):
        config = get_config()
        data_dir = config.app.data_dir
        import os
        os.makedirs(data_dir, exist_ok=True)
        self.store = TaskStore(os.path.join(data_dir, "background_tasks.db"))
        self._tasks: Dict[str, BackgroundTask] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running: Dict[str, asyncio.Task] = {}
        self._res_mgr = get_resource_manager()
        self._pool_size = self._recommended_pool_size()
        self._semaphore = asyncio.Semaphore(self._pool_size)
        self._throttle_factor = 1.0  # 1.0 = full, lowered under pressure
        self._paused_background = False
        self._loop_task: Optional[asyncio.Task] = None
        self._running_flag = False
        # FIX 2: named task factories so persisted tasks can be re-executed
        # after restart (coroutines are not serializable). A factory returns the
        # coroutine callable for a given (name) — used during recovery.
        self._factories: Dict[str, Callable[..., Awaitable[None]]] = {}

    def register_factory(self, name: str, coroutine: Callable[..., Awaitable[None]]) -> None:
        """Register a named coroutine so recovered tasks can be rebuilt."""
        self._factories[name] = coroutine

    def _resolve_coroutine(self, task: BackgroundTask) -> Optional[Callable[..., Awaitable[None]]]:
        if task.coroutine is not None:
            return task.coroutine
        # Recovery path: rebuild from the registered factory by name.
        return self._factories.get(task.name)

    # --- config helpers -------------------------------------------------
    def _recommended_pool_size(self) -> int:
        mode = self._res_mgr.get_effective_mode()
        return {
            "ULTRA_LOW": 2,
            "LOW": 2,
            "BALANCED": 4,
            "PERFORMANCE": 6,
        }.get(mode, 3)

    # --- public API (Section 46) --------------------------------------
    def create(
        self,
        name: str,
        coroutine: Callable[..., Awaitable[None]],
        *args,
        priority: str = TaskPriority.NORMAL.value,
        type: str = TaskType.BACKGROUND.value,
        max_cpu: int = 25,
        max_memory_mb: int = 300,
        network_required: bool = False,
        gpu_required: bool = False,
        estimated_duration_s: int = 0,
        max_retries: int = 2,
        retryable: bool = True,
        dependencies: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        tid = f"task_{uuid.uuid4().hex[:8]}"
        task = BackgroundTask(
            id=tid, name=name, priority=priority, type=type,
            coroutine=coroutine, args=args, kwargs=kwargs,
            max_cpu=max_cpu, max_memory_mb=max_memory_mb,
            network_required=network_required, gpu_required=gpu_required,
            estimated_duration_s=estimated_duration_s,
            max_retries=max_retries, retryable=retryable,
            dependencies=dependencies or [],
        )
        self._tasks[tid] = task
        self.store.upsert(task)
        self._enqueue(task)
        logger.info(f"Task created: {name} ({tid}) prio={priority}")
        return tid

    def _enqueue(self, task: BackgroundTask):
        task.status = TaskStatus.QUEUED.value
        self.store.upsert(task)
        rank = _PRIORITY_RANK.get(TaskPriority(task.priority), 3)
        # (priority_rank, created_at, id) -> stable ordering
        self._queue.put_nowait((rank, task.created_at, task.id))
        self._emit("task.created", task)

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        return self._tasks.get(task_id)

    def list(self) -> List[dict]:
        return [t.to_dict() for t in self._tasks.values()]

    def pause(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        if not t or t.status in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value,
                                 TaskStatus.CANCELLED.value):
            return False
        # Write a checkpoint so the task can resume from where it stopped (29).
        self.checkpoint(task_id, {**t.checkpoint, "paused_at": time.time(),
                                  "progress": t.progress})
        # If it is actively running, cancel the underlying asyncio task so it
        # actually stops consuming resources (FIX 3 — real pause).
        running = self._running.get(task_id)
        if running and not running.done():
            running.cancel()
        t.status = TaskStatus.PAUSED.value
        self.store.upsert(t)
        self._emit("task.paused", t)
        logger.info(f"Task paused: {t.name} ({task_id})")
        return True

    def resume(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        if not t or t.status != TaskStatus.PAUSED.value:
            return False
        self._enqueue(t)
        return True

    def cancel(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        if not t:
            return False
        # Actually stop a running asyncio task (FIX 3 — real cancel).
        running = self._running.pop(task_id, None)
        if running and not running.done():
            running.cancel()
        t.status = TaskStatus.CANCELLED.value
        t.finished_at = time.time()
        self.store.upsert(t)
        self._emit("task.cancelled", t)
        logger.info(f"Task cancelled: {t.name} ({task_id})")
        return True

    def retry(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        if not t or t.status != TaskStatus.FAILED.value:
            return False
        t.status = TaskStatus.CREATED.value
        t.error = None
        t._attempt = 0
        self._enqueue(t)
        self._emit("task.resumed", t)
        return True

    def checkpoint(self, task_id: str, data: dict) -> None:
        t = self._tasks.get(task_id)
        if t:
            t.checkpoint = data
            self.store.upsert(t)

    # --- scheduler loop ------------------------------------------------
    async def start(self):
        if self._running_flag:
            return
        self._running_flag = True
        # Resume unfinished tasks from a previous run (Section 30/53).
        self._resume_persisted()
        self._loop_task = asyncio.create_task(self._scheduler_loop())
        logger.info(f"BackgroundTaskEngine started (pool={self._pool_size})")

    async def stop(self):
        self._running_flag = False
        for t in list(self._running.values()):
            t.cancel()
        if self._loop_task:
            self._loop_task.cancel()
        # FIX 1: checkpoint every in-flight task so a later boot can resume.
        self.checkpoint_all()

    def checkpoint_all(self) -> None:
        """Persist progress for all live tasks (Section 29/52)."""
        for task in self._tasks.values():
            if task.status in (TaskStatus.RUNNING.value, TaskStatus.PAUSED.value,
                               TaskStatus.QUEUED.value, TaskStatus.WAITING.value):
                try:
                    self.store.upsert(task)
                except Exception as e:
                    logger.warning(f"checkpoint_all: {e}")

    def _resume_persisted(self):
        """FIX 2: recover tasks from the previous run (Section 30/53).

        Persisted rows are rebuilt into BackgroundTask objects and re-enqueued
        if resumable (QUEUED/RUNNING/PAUSED/WAITING and has a known factory).
        Tasks whose coroutine cannot be resolved are marked FAILED with a clear
        reason instead of silently vanishing.
        """
        try:
            rows = self.store.load_unfinished()
        except Exception as e:
            logger.warning(f"Could not resume persisted tasks: {e}")
            return
        for row in rows:
            try:
                task = self._task_from_row(row)
                self._tasks[task.id] = task
                resumable = task.status in (
                    TaskStatus.QUEUED.value, TaskStatus.RUNNING.value,
                    TaskStatus.WAITING.value, TaskStatus.PAUSED.value,
                )
                if not resumable:
                    continue
                # If we can't rebuild the coroutine, the task can't run.
                if resumable and self._resolve_coroutine(task) is None:
                    logger.warning(
                        f"Task '{task.name}' recovered but no factory registered; marking FAILED"
                    )
                    task.status = TaskStatus.FAILED.value
                    task.error = "recovered without executable coroutine"
                    self.store.upsert(task)
                    self._emit("task.failed", task)
                    continue
                # Re-enqueue: PAUSED stays PAUSED until user resumes; others run.
                if task.status == TaskStatus.PAUSED.value:
                    continue
                task.status = TaskStatus.QUEUED.value
                self.store.upsert(task)
                self._enqueue(task)
                logger.info(f"Recovered task on boot: {task.name} ({task.id}) -> {task.status}")
            except Exception as e:
                logger.error(f"Failed to recover task {row.get('id')}: {e}")

    @staticmethod
    def _task_from_row(row: dict) -> BackgroundTask:
        payload = json.loads(row.get("payload") or "{}")
        retry = json.loads(row.get("retry_policy") or "{}")
        res = json.loads(row.get("resources") or "{}")
        deps = json.loads(row.get("dependencies") or "[]")
        return BackgroundTask(
            id=row["id"], name=row["name"], priority=row.get("priority", "NORMAL"),
            type=row.get("type", "BACKGROUND"), status=row.get("status", "QUEUED"),
            progress=row.get("progress", 0.0),
            args=tuple(payload.get("args", [])), kwargs=payload.get("kwargs", {}),
            max_cpu=res.get("max_cpu", 25), max_memory_mb=res.get("max_memory_mb", 300),
            network_required=res.get("network", False), gpu_required=res.get("gpu", False),
            estimated_duration_s=res.get("estimated", 0),
            max_retries=retry.get("max_retries", 2),
            retry_backoff_s=retry.get("backoff", 5.0),
            retryable=retry.get("retryable", True),
            created_at=row.get("created_at", time.time()),
            started_at=row.get("started_at"), finished_at=row.get("finished_at"),
            checkpoint=json.loads(row.get("checkpoint") or "{}"),
            dependencies=deps, error=row.get("error"),
            result=json.loads(row["result"]) if row.get("result") else None,
        )

    async def _scheduler_loop(self):
        while self._running_flag:
            try:
                _, _, tid = await self._queue.get()
            except asyncio.CancelledError:
                break
            task = self._tasks.get(tid)
            if not task or task.status == TaskStatus.CANCELLED.value:
                self._queue.task_done()
                continue
            await self._maybe_wait_dependencies(task)
            # Resource-aware gating (Section 27/28/48)
            if self._should_throttle(task):
                self._queue.put_nowait((_PRIORITY_RANK.get(TaskPriority(task.priority), 3),
                                         time.time(), tid))
                self._queue.task_done()
                await asyncio.sleep(1.0)
                continue

            task.status = TaskStatus.RUNNING.value
            task.started_at = time.time()
            self.store.upsert(task)
            self._emit("task.started", task)
            # Bound concurrency (Section 22).
            self._running[tid] = asyncio.create_task(self._run_task(task))
            self._queue.task_done()

    async def _maybe_wait_dependencies(self, task: BackgroundTask):
        if not task.dependencies:
            return
        for dep in task.dependencies:
            dep_task = self._tasks.get(dep)
            if dep_task and dep_task.status not in (TaskStatus.COMPLETED.value,):
                task.status = TaskStatus.WAITING.value
                self.store.upsert(task)
                self._emit("task.waiting", task)
                while self._running_flag:
                    if dep_task.status == TaskStatus.COMPLETED.value:
                        break
                    if dep_task.status in (TaskStatus.FAILED.value, TaskStatus.CANCELLED.value):
                        task.status = TaskStatus.FAILED.value
                        task.error = f"Dependency {dep} did not complete"
                        self.store.upsert(task)
                        self._emit("task.failed", task)
                        return
                    await asyncio.sleep(0.5)

    def _should_throttle(self, task: BackgroundTask) -> bool:
        # Delegate to the authoritative ResourceManager policy (Section 27/48).
        return self._res_mgr.should_throttle(task.priority)

    async def _run_task(self, task: BackgroundTask):
        async with self._semaphore:
            try:
                coro = self._resolve_coroutine(task)
                if coro is None:
                    raise ValueError("Task has no resolvable coroutine")
                # Inject progress + checkpoint helpers into kwargs.
                kwargs = dict(task.kwargs)
                kwargs.setdefault("_task", task)
                kwargs.setdefault("_manager", self)
                await coro(*task.args, **kwargs)
                task.status = TaskStatus.COMPLETED.value
                task.progress = 100.0
                task.finished_at = time.time()
                self.store.upsert(task)
                self._emit("task.completed", task)
                self._notify_completion(task)
            except asyncio.CancelledError:
                # Real pause/cancel requested via pause()/cancel() already set
                # the authoritative status; keep it. Remove from the running map.
                self._running.pop(task.id, None)
                self.store.upsert(task)
                # Do NOT re-raise: this is an expected cooperative cancellation.
                return
            except Exception as e:
                task._attempt += 1
                task.error = str(e)[:300]
                logger.error(f"Task '{task.name}' failed (attempt {task._attempt}): {e}")
                if task.retryable and task._attempt <= task.max_retries:
                    task.status = TaskStatus.QUEUED.value
                    self.store.upsert(task)
                    self._emit("task.failed", task)
                    await asyncio.sleep(task.retry_backoff_s)
                    self._queue.put_nowait((_PRIORITY_RANK.get(TaskPriority(task.priority), 3),
                                             time.time(), task.id))
                else:
                    task.status = TaskStatus.FAILED.value
                    task.finished_at = time.time()
                    self.store.upsert(task)
                    self._emit("task.failed", task)
            finally:
                # Always drop the handle so it can't leak (FIX 3).
                self._running.pop(task.id, None)

    # --- resource controls (Section 48/49/75) -------------------------
    def set_background_paused(self, paused: bool):
        self._paused_background = paused
        # Keep the authoritative ResourceManager in sync (Section 48/51).
        if paused:
            self._res_mgr.pause_background_tasks()
        else:
            self._res_mgr.resume_background_tasks()
        logger.info(f"Background tasks {'PAUSED' if paused else 'RESUMED'}")

    def set_pool_size(self, n: int):
        self._pool_size = max(1, min(16, n))
        self._semaphore = asyncio.Semaphore(self._pool_size)
        logger.info(f"Worker pool resized to {self._pool_size}")

    # --- events --------------------------------------------------------
    def _emit(self, event_type: str, task: BackgroundTask):
        try:
            asyncio.get_running_loop().create_task(
                get_event_bus().publish(event_type, task.to_dict(), source="task_engine")
            )
        except RuntimeError:
            pass

    def _notify_completion(self, task: BackgroundTask):
        try:
            asyncio.get_running_loop().create_task(
                get_event_bus().publish(
                    "notification.created",
                    {
                        "title": "Background task completed",
                        "message": f"{task.name} finished.",
                        "task_id": task.id,
                        "priority": task.priority,
                    },
                    source="task_engine",
                )
            )
        except RuntimeError:
            pass


_task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    return _task_manager
