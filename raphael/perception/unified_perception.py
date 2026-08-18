"""
Unified Perception Engine for Raphael AI Assistant.
Aggregates audio, speech, screen structural state, clipboard, and active system events.
"""

import time
import asyncio
from typing import Dict, Any, Optional
from raphael.perception.screen_understanding import get_screen_observer
from raphael.platform.factory import get_platform_adapter
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger

logger = get_logger("perception.unified")

class UnifiedPerception:
    def __init__(self):
        self.screen_observer = get_screen_observer()

    async def observe_environment(self) -> Dict[str, Any]:
        start_time = time.time()
        screen_state = self.screen_observer.get_structural_state()
        adapter = get_platform_adapter()
        clipboard_state = adapter.get_clipboard_text().get("result", {}).get("text", "")

        observation = {
            "source": "unified_perception",
            "timestamp": time.time(),
            "confidence": 0.95,
            "payload": {
                "active_app": screen_state["active_app"],
                "window_title": screen_state["window_title"],
                "activity": screen_state["detected_activity"],
                "visible_error": screen_state.get("visible_error"),
                "clipboard_length": len(clipboard_state),
                "platform": adapter.os_name
            }
        }

        await get_event_bus().publish(
            "perception.observation",
            observation,
            source="unified_perception"
        )

        logger.debug(f"Observation captured: App={screen_state['active_app']} | Activity={screen_state['detected_activity']}")
        return observation

_unified_perception = UnifiedPerception()

def get_unified_perception() -> UnifiedPerception:
    return _unified_perception
