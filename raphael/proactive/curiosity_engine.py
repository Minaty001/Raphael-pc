"""
Curiosity Engine for Raphael AI Assistant.
Generates targeted clarification or learning questions when information gaps are detected.
"""

import time
from typing import Dict, Any, Optional
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger

logger = get_logger("proactive.curiosity")

class CuriosityEngine:
    async def generate_curiosity_question(self, topic: str, context: str) -> Dict[str, Any]:
        question = f"I noticed you frequently interact with '{topic}'. Should I set up a dedicated shortcut or default preference for this?"
        
        payload = {
            "topic": topic,
            "question": question,
            "context": context,
            "timestamp": time.time()
        }

        await get_event_bus().publish("curiosity.question_generated", payload, source="curiosity_engine")
        logger.info(f"Curiosity Question Generated: '{question}'")
        return payload

_curiosity_engine = CuriosityEngine()

def get_curiosity_engine() -> CuriosityEngine:
    return _curiosity_engine
