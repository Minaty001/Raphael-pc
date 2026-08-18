"""
Proactive Conversation Engine for Raphael AI Assistant.
Initiates timely, context-aware suggestions with strict interruption policies and hourly budgets.
"""

import time
from typing import Dict, Any, Optional, List
from raphael.core.configuration import get_config
from raphael.core.event_bus import get_event_bus
from raphael.brain.open_loops import get_open_loop_tracker
from raphael.core.logging import get_logger

logger = get_logger("proactive.engine")

class InterruptionPolicy:
    URGENT = "URGENT"          # System alerts, dangerous failures
    HIGH_VALUE = "HIGH_VALUE"      # Open loop follow-ups, build fixes
    LOW_VALUE = "LOW_VALUE"       # General suggestions
    IGNORE = "IGNORE"          # Low relevance noise

class ProactiveEngine:
    def __init__(self):
        self.config = get_config()
        self.last_proactive_time: float = 0.0
        self.proactive_count_this_hour: int = 0
        self.hour_window_start: float = time.time()

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

        open_loops = get_open_loop_tracker().list_open_loops()
        active_app = context_summary.get("recent_screen", {}).get("active_app", "")

        # 1. Check High-Value Open Loop follow-up
        if open_loops:
            top_loop = open_loops[0]
            topic = top_loop["topic"]
            
            # Avoid repeating too quickly
            if time.time() - self.last_proactive_time < 300:
                return None

            suggestion = f"Yesterday you were working on '{topic}'. Should we continue that investigation?"
            
            self.last_proactive_time = time.time()
            self.proactive_count_this_hour += 1

            payload = {
                "policy": InterruptionPolicy.HIGH_VALUE,
                "topic": topic,
                "text": suggestion,
                "timestamp": self.last_proactive_time
            }

            await get_event_bus().publish("proactive.topic_generated", payload, source="proactive_engine")
            logger.info(f"Proactive Topic Generated: '{suggestion}'")
            return payload

        return None

_proactive_engine = ProactiveEngine()

def get_proactive_engine() -> ProactiveEngine:
    return _proactive_engine
