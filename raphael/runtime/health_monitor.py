"""
Runtime Health Monitor & Watchdog for Raphael v3 Always-Alive Runtime.
Section 9 (Health Monitor) + Section 10 (Watchdog).

The health monitor produces a per-component status snapshot that the UI/tray
render as "ALIVE" (Section 8). The watchdog keeps every registered worker alive:
if a worker task crashes, it is restarted, state is restored, and the UI is
notified (Section 10). No single background worker may kill Raphael.
"""

import asyncio
import time
import shutil
import psutil
from typing import Dict, Any, Callable, Awaitable, Optional
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus
from raphael.core.configuration import get_config

logger = get_logger("runtime.health")


class RuntimeHealthMonitor:
    def __init__(self):
        # Each entry: name -> {"status", "detail", "last_checked"}
        self._components: Dict[str, Dict[str, Any]] = {}
        self._start_time = time.time()
        self._probes: Dict[str, Callable[[], Awaitable[Dict[str, Any]]]] = {}
        self._register_default_probes()

    def register(self, name: str, status: str = "ok", detail: str = "") -> None:
        self._components[name] = {
            "status": status,
            "detail": detail,
            "last_checked": time.time(),
        }

    def update(self, name: str, status: str, detail: str = "") -> None:
        if name not in self._components:
            self.register(name, status, detail)
            return
        self._components[name]["status"] = status
        self._components[name]["detail"] = detail
        self._components[name]["last_checked"] = time.time()

    def register_probe(self, name: str, probe: Callable[[], Awaitable[Dict[str, Any]]]) -> None:
        """Register an active health probe that runs on each snapshot (FIX 10)."""
        self._probes[name] = probe
        if name not in self._components:
            self.register(name, "unknown", "probe registered")

    def _register_default_probes(self):
        cfg = get_config()
        # Memory DB probe: can we open the SQLite store?
        async def _probe_memory() -> Dict[str, Any]:
            try:
                from raphael.memory.long_term import get_long_term_memory
                ltm = get_long_term_memory()
                conn = ltm._get_connection()
                conn.execute("SELECT 1 FROM memories LIMIT 1")
                conn.close()
                return {"status": "healthy", "detail": "memory db reachable"}
            except Exception as e:
                return {"status": "error", "detail": f"memory db: {e}"}

        # WebSocket probe: report real client connectivity (P0 #29).
        # "connected" only when >=1 client is attached; otherwise "listening"
        # (server is up but no UI connected yet) — never a false "connected".
        async def _probe_websocket() -> Dict[str, Any]:
            try:
                from raphael.network.websocket import get_ws_manager
                n = len(get_ws_manager().active_connections)
                if n > 0:
                    return {"status": "connected", "detail": f"{n} client(s) connected"}
                return {"status": "listening", "detail": "gateway up, no client connected"}
            except Exception as e:
                return {"status": "error", "detail": f"ws: {e}"}

        # LLM probe: is a provider reachable?
        async def _probe_llm() -> Dict[str, Any]:
            try:
                from raphael.brain.llm_router import get_llm_router
                name, _ = await get_llm_router().get_active_provider()
                return {"status": "available", "detail": f"provider {name}"}
            except Exception as e:
                return {"status": "error", "detail": f"llm: {e}"}

        # Voice probe: mic + wakeword availability (non-fatal if missing).
        async def _probe_voice() -> Dict[str, Any]:
            try:
                from raphael.voice.wakeword import get_wake_word_detector
                wd = get_wake_word_detector()
                return {"status": "ready" if wd.enabled else "paused",
                        "detail": "wake detector" + ("" if wd.enabled else " (disabled)")}
            except Exception as e:
                return {"status": "error", "detail": f"voice: {e}"}

        self.register_probe("memory", _probe_memory)
        self.register_probe("websocket", _probe_websocket)
        self.register_probe("llm", _probe_llm)
        self.register_probe("voice", _probe_voice)

    async def snapshot(self) -> Dict[str, Any]:
        """Section 9 example shape, with AUTHORITATIVE live probes (FIX 10)."""
        now = time.time()
        # Run registered probes to get real status (not just startup flags).
        for name, probe in self._probes.items():
            try:
                res = await probe()
                self._components.setdefault(name, {})
                self._components[name]["status"] = res["status"]
                self._components[name]["detail"] = res.get("detail", "")
                self._components[name]["last_checked"] = now
            except Exception as e:
                self._components.setdefault(name, {})
                self._components[name]["status"] = "error"
                self._components[name]["detail"] = str(e)[:120]
                self._components[name]["last_checked"] = now

        # Core/wakeword/scheduler are process-internal: derive from running flags.
        return {
            "runtime": "alive",
            "uptime_seconds": int(now - self._start_time),
            "components": {
                name: {
                    "status": info["status"],
                    "detail": info.get("detail", ""),
                    "stale_seconds": round(now - info.get("last_checked", now), 1),
                }
                for name, info in self._components.items()
            },
            "timestamp": now,
        }

    def is_healthy(self) -> bool:
        return all(
            info["status"] in ("ok", "ready", "alive", "running", "available",
                               "healthy", "connected", "listening")
            for info in self._components.values()
        )


_health_monitor = RuntimeHealthMonitor()


def get_health_monitor() -> RuntimeHealthMonitor:
    return _health_monitor


# ----------------------------------------------------------------------
# Watchdog (Section 10)
# ----------------------------------------------------------------------
WorkerFn = Callable[[], Awaitable[None]]


class Watchdog:
    """Supervises long-lived background worker coroutines."""

    def __init__(self, health: RuntimeHealthMonitor):
        self._health = health
        self._workers: Dict[str, Dict[str, Any]] = {}
        self._running = False

    def register_worker(
        self,
        name: str,
        coro_fn: WorkerFn,
        restart: bool = True,
        max_restarts: int = 10,
        component_key: Optional[str] = None,
    ) -> None:
        self._workers[name] = {
            "fn": coro_fn,
            "task": None,
            "restart": restart,
            "max_restarts": max_restarts,
            "restarts": 0,
            "component_key": component_key or name,
            "crashed": False,
        }
        self._health.register(
            component_key or name, "running" if restart else "ok", "worker registered"
        )

    def start(self) -> None:
        self._running = True
        for name in self._workers:
            self._spawn(name)

    def _spawn(self, name: str) -> None:
        w = self._workers[name]
        w["task"] = asyncio.create_task(self._supervise(name), name=f"watchdog:{name}")

    async def _supervise(self, name: str) -> None:
        w = self._workers[name]
        while self._running and w["restart"]:
            try:
                await w["fn"]()
                # fn returned cleanly; if still running we treat as stop.
                if not self._running:
                    break
                # Should not normally return; if it does, respawn after delay.
                await asyncio.sleep(1.0)
                if w["restarts"] >= w["max_restarts"]:
                    logger.error(f"Worker '{name}' exceeded max restarts; giving up.")
                    self._health.update(w["component_key"], "error", "max restarts exceeded")
                    break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                w["crashes"] = w.get("crashes", 0) + 1
                w["restarts"] += 1
                logger.error(f"Watchdog: worker '{name}' crashed: {e}", exc_info=True)
                self._health.update(w["component_key"], "error", str(e)[:200])
                # Section 10: notify UI.
                await get_event_bus().publish(
                    "runtime.worker_crashed",
                    {"worker": name, "error": str(e), "restart": w["restart"]},
                    source="watchdog",
                )
                if w["restarts"] >= w["max_restarts"]:
                    logger.error(f"Worker '{name}' exceeded max restarts; giving up.")
                    self._health.update(w["component_key"], "error", "max restarts exceeded")
                    break
                await asyncio.sleep(2.0)

    def stop(self) -> None:
        self._running = False
        for w in self._workers.values():
            if w["task"]:
                w["task"].cancel()

    def status(self) -> Dict[str, Any]:
        return {
            name: {
                "alive": (w["task"] is not None and not w["task"].done()),
                "restarts": w["restarts"],
            }
            for name, w in self._workers.items()
        }


_watchdog = Watchdog(_health_monitor)


def get_watchdog() -> Watchdog:
    return _watchdog
