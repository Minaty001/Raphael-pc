"""
Proactive Conversation Engine for Raphael Always-Alive Runtime.

FIX 12 — Proactive intelligence (Sections 40, 59, 78).
Initiates timely, context-aware suggestions with strict interruption policies
and hourly budgets. Now actually *run* on a schedule (it was previously defined
but never invoked) and delivers opportunities through the event bus so the UI
can show a non-intrusive notification (Sections 57-59).
"""

import asyncio
import time
from typing import Dict, Any, Optional, List

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus
from raphael.brain.open_loops import get_open_loop_tracker
from raphael.core.resource_manager import get_resource_manager
from raphael.runtime.health_monitor import get_health_monitor

logger = get_logger("proactive.engine")


class InterruptionPolicy:
    URGENT = "URGENT"          # System alerts, dangerous failures
    HIGH_VALUE = "HIGH_VALUE"      # Open loop follow-ups, build fixes
    LOW_VALUE = "LOW_VALUE"       # General suggestions
    IGNORE = "IGNORE"          # Low relevance noise


class ProactiveEngine:
    def __init__(self):
        self.config = get_config()
        self._res_mgr = get_resource_manager()
        self._health = get_health_monitor()
        self.last_proactive_time: float = 0.0
        self.proactive_count_this_hour: int = 0
        self.hour_window_start: float = time.time()
        self._running = False
        self._task: Any = None
        self._interval_s = 90  # evaluation cadence during idle

    def _check_budget(self) -> bool:
        now = time.time()
        if now - self.hour_window_start > 3600:
            self.hour_window_start = now
            self.proactive_count_this_hour = 0
        max_allowed = self.config.proactive.max_interruptions_per_hour
        return self.proactive_count_this_hour < max_allowed

    async def evaluate_proactive_opportunity(self, context_summary: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.config.proactive.enabled or not self._check_budget():
            return None
        # Only act when resources allow and the runtime is healthy (Section 75).
        if not self._res_mgr.can_run("LOW") or not self._health.is_healthy():
            return None

        open_loops = get_open_loop_tracker().list_open_loops()
        active_app = context_summary.get("recent_screen", {})
        if isinstance(active_app, dict):
            active_app = active_app.get("active_app", "")
        else:
            active_app = ""

        if open_loops:
            top_loop = open_loops[0]
            topic = top_loop["topic"]
            if time.time() - self.last_proactive_time < 300:
                return None
            suggestion = (f"Yesterday you were working on '{topic}'. "
                          f"Should we continue that investigation?")
            self.last_proactive_time = time.time()
            self.proactive_count_this_hour += 1
            payload = {
                "policy": InterruptionPolicy.HIGH_VALUE,
                "topic": topic,
                "text": suggestion,
                "timestamp": self.last_proactive_time,
            }
            await get_event_bus().publish("proactive.topic_generated", payload, source="proactive_engine")
            logger.info(f"Proactive Topic Generated: '{suggestion}'")
            return payload
        return None

    # --- FIX 12: scheduled evaluation loop -----------------------------
    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Proactive Engine started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self):
        from raphael.memory.working_memory import get_working_memory
        while self._running:
            try:
                await asyncio.sleep(self._interval_s)
                # Real context probe: use the working-memory summary the
                # cognitive loop populates with live perception (recent_screen),
                # instead of a hardcoded empty context (Section 14/40).
                ctx = get_working_memory().get_summary()
                await self.evaluate_proactive_opportunity(ctx)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Proactive loop error: {e}")


_engine = ProactiveEngine()


def get_proactive_engine() -> ProactiveEngine:
    return _engine

