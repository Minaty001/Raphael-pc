"""
Background Intelligence Engine for Raphael Always-Alive Runtime.

FIX 11 — Cognitive background work (Sections 39, 77).
During idle periods Raphael performs low-priority cognitive maintenance:
  * Memory consolidation (dedupe / promote important memories)
  * Open-loop review (surface unresolved topics)
  * Learning loop (detect patterns, update user model)
  * Reflection sweep (turn recent episodes into lessons)

All of this is LOW/IDLE priority, resource-aware (uses the ResourceManager
policy), and runs independently of the UI / foreground voice (Section 64).
Tasks are registered with the TaskManager so they persist and recover.
"""

import asyncio
import time
from typing import Dict, Any, List

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus
from raphael.runtime.tasks import get_task_manager, TaskPriority
from raphael.core.resource_manager import get_resource_manager

logger = get_logger("runtime.background_intelligence")


async def _consolidate_memory(**kwargs):
    """Low-priority memory maintenance (Section 32/77)."""
    try:
        from raphael.memory.memory_manager import get_memory_manager
        mm = get_memory_manager()
        if hasattr(mm, "consolidate"):
            await mm.consolidate()
        logger.info("Background: memory consolidation pass complete")
    except Exception as e:
        logger.warning(f"Memory consolidation error: {e}")


async def _review_open_loops(**kwargs):
    """Surface unresolved topics for the user later (Section 39)."""
    try:
        from raphael.brain.open_loops import get_open_loop_tracker
        loops = get_open_loop_tracker().list_open_loops()
        if loops:
            logger.info(f"Background: {len(loops)} open loop(s) tracked")
            await get_event_bus().publish(
                "background.open_loops_reviewed",
                {"count": len(loops), "topics": [l["topic"] for l in loops[:5]]},
                source="background_intelligence",
            )
    except Exception as e:
        logger.warning(f"Open-loop review error: {e}")


async def _learning_loop(**kwargs):
    """Detect patterns / update user model (Section 77)."""
    try:
        from raphael.learning.learning_engine import get_learning_engine
        le = get_learning_engine()
        if hasattr(le, "background_reflect"):
            await le.background_reflect()
        logger.info("Background: learning loop pass complete")
    except Exception as e:
        logger.warning(f"Learning loop error: {e}")


class BackgroundIntelligenceEngine:
    def __init__(self):
        self.config = get_config()
        self._task_manager = get_task_manager()
        self._res_mgr = get_resource_manager()
        self._interval_s = 120  # idle sweep cadence
        self._running = False
        self._task: Any = None
        # Register factories so persisted cognitive tasks can recover (FIX 2).
        self._task_manager.register_factory("bg:memory_consolidation", _consolidate_memory)
        self._task_manager.register_factory("bg:open_loop_review", _review_open_loops)
        self._task_manager.register_factory("bg:learning_loop", _learning_loop)

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._idle_loop())
        logger.info("Background Intelligence Engine started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _idle_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self._interval_s)
                if not self._res_mgr.can_run("IDLE"):
                    # Resource pressure: skip this sweep (Section 48/75).
                    continue
                # Schedule one of each low-priority cognitive task. If a previous
                # instance is still queued/running, the scheduler dedupes by name.
                self._schedule("bg:memory_consolidation", _consolidate_memory, "IDLE")
                self._schedule("bg:open_loop_review", _review_open_loops, "IDLE")
                self._schedule("bg:learning_loop", _learning_loop, "LOW")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Background intelligence sweep error: {e}")

    def _schedule(self, name: str, coro, priority: str):
        # Avoid stacking duplicates: only schedule if not already present.
        existing = [t for t in self._task_manager._tasks.values() if t.name == name]
        if existing:
            return
        self._task_manager.create(
            name=name,
            coroutine=coro,
            priority=priority,
            type="BACKGROUND",
            max_cpu=10,
            max_memory_mb=200,
            estimated_duration_s=30,
        )
        logger.debug(f"Background intelligence scheduled: {name}")


_engine = BackgroundIntelligenceEngine()


def get_background_intelligence() -> BackgroundIntelligenceEngine:
    return _engine
