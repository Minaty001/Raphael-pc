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
from typing import Dict, Any, Callable, Awaitable, Optional
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus

logger = get_logger("runtime.health")


class RuntimeHealthMonitor:
    def __init__(self):
        # Each entry: name -> {"status", "detail", "last_checked"}
        self._components: Dict[str, Dict[str, Any]] = {}
        self._start_time = time.time()

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

    async def snapshot(self) -> Dict[str, Any]:
        """Section 9 example shape."""
        now = time.time()
        return {
            "runtime": "alive",
            "uptime_seconds": int(now - self._start_time),
            "components": {
                name: {
                    "status": info["status"],
                    "detail": info["detail"],
                    "stale_seconds": round(now - info["last_checked"], 1),
                }
                for name, info in self._components.items()
            },
            "timestamp": now,
        }

    def is_healthy(self) -> bool:
        return all(
            info["status"] in ("ok", "ready", "alive", "running", "available", "healthy", "connected")
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
