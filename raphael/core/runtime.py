"""
Raphael Runtime Orchestrator.
Implements lazy startup phases and lifecycle management for Cognitive Brain components.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus
from raphael.core.state_manager import get_state_manager, AssistantState
from raphael.core.resource_manager import get_resource_manager
from raphael.core.scheduler import get_scheduler
from raphael.platform.factory import get_platform_adapter
from raphael.tools.registry import get_tool_registry
from raphael.brain.cognitive_runtime import get_cognitive_runtime

logger = get_logger("core.runtime")

class RaphaelRuntime:
    def __init__(self):
        self.config = get_config()
        self._running = False
        self._start_time = 0.0
        self._perception_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return

        self._start_time = time.time()
        logger.info("=== STARTING RAPHAEL AI ASSISTANT RUNTIME ===")

        # Phase 1: Core Initialization
        logger.info("PHASE 1: Core Initialized")

        # Phase 2: Platform & System Adapters
        platform = get_platform_adapter()
        logger.info(f"PHASE 2: Platform adapter loaded ({platform.os_name})")

        # Phase 3: Load Tool Registry & Security
        import raphael.tools.system
        import raphael.tools.applications
        import raphael.tools.filesystem
        import raphael.tools.browser
        import raphael.tools.developer
        import raphael.tools.media

        tools = get_tool_registry().list_tools()
        logger.info(f"PHASE 3: Registered {len(tools)} tools")

        # Phase 4: Scheduler
        scheduler = get_scheduler()
        await scheduler.start()
        logger.info("PHASE 4: Scheduler active")

        # Phase 5: Cognitive Brain Subsystems Initialization
        cog = get_cognitive_runtime()
        logger.info("PHASE 5: Cognitive Brain & Memory initialized")

        # Phase 6: Periodic Perception Background Loop
        self._running = True
        self._perception_task = asyncio.create_task(self._run_perception_loop())
        logger.info("PHASE 6: Background perception loop active")

        state_mgr = get_state_manager()
        await state_mgr.set_state(AssistantState.IDLE, {"startup_time_s": time.time() - self._start_time})
        logger.info("=== RAPHAEL COGNITIVE ASSISTANT IS READY ===")

    async def stop(self) -> None:
        if not self._running:
            return
        logger.info("Stopping Raphael Assistant...")
        self._running = False
        if self._perception_task:
            self._perception_task.cancel()
            self._perception_task = None
        await get_scheduler().stop()
        await get_state_manager().set_state(AssistantState.OFFLINE)
        logger.info("Raphael Assistant stopped.")

    async def _run_perception_loop(self):
        cog = get_cognitive_runtime()
        while self._running:
            try:
                await cog.execute_cognitive_cycle()
            except Exception as e:
                logger.warning(f"Error in background perception loop: {e}")
            await asyncio.sleep(15.0)  # Low resource periodic cycle

_runtime_instance = RaphaelRuntime()

def get_runtime() -> RaphaelRuntime:
    return _runtime_instance
