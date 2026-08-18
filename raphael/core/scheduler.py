"""
Task Scheduler for Raphael AI Assistant.
Schedules reminders, delayed actions, and background tasks.
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Callable, Awaitable, List, Optional
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus

logger = get_logger("scheduler")

class ScheduledTask:
    def __init__(self, task_id: str, title: str, execute_at: float, action: Callable[[], Awaitable[None]], payload: Dict[str, Any]):
        self.task_id = task_id
        self.title = title
        self.execute_at = execute_at
        self.action = action
        self.payload = payload
        self.status = "pending"

class TaskScheduler:
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._loop_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started.")

    async def stop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        logger.info("Scheduler stopped.")

    def schedule_task(self, title: str, delay_seconds: float, action: Callable[[], Awaitable[None]], payload: Optional[Dict[str, Any]] = None) -> str:
        task_id = str(uuid.uuid4())[:8]
        execute_at = time.time() + delay_seconds
        task = ScheduledTask(task_id, title, execute_at, action, payload or {})
        self._tasks[task_id] = task
        logger.info(f"Task scheduled: '{title}' in {delay_seconds:.1f}s (ID: {task_id})")
        return task_id

    def list_tasks(self) -> List[Dict[str, Any]]:
        now = time.time()
        return [
            {
                "task_id": t.task_id,
                "title": t.title,
                "execute_at": t.execute_at,
                "time_remaining_seconds": max(0, t.execute_at - now),
                "status": t.status,
                "payload": t.payload
            }
            for t in self._tasks.values()
        ]

    async def _run_loop(self) -> None:
        while self._running:
            now = time.time()
            due_tasks = [t for t in self._tasks.values() if t.status == "pending" and t.execute_at <= now]
            
            for task in due_tasks:
                task.status = "executing"
                try:
                    logger.info(f"Executing scheduled task: {task.title}")
                    await task.action()
                    task.status = "completed"
                    await get_event_bus().publish(
                        "notification.created",
                        {"title": "Reminder", "message": task.title, "task_id": task.task_id},
                        source="scheduler"
                    )
                except Exception as e:
                    task.status = "failed"
                    logger.error(f"Task execution failed: {e}", exc_info=True)

            await asyncio.sleep(1.0)

_scheduler_instance = TaskScheduler()

def get_scheduler() -> TaskScheduler:
    return _scheduler_instance
