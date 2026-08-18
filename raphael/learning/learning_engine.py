"""
Learning Engine for Raphael AI Assistant.
Observes tool outcomes, user corrections, and interaction patterns to generate learning candidates.
"""

import time
from typing import Dict, Any, List, Optional
from raphael.memory.user_model import get_user_model
from raphael.memory.semantic_memory import get_semantic_memory, SemanticType
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger

logger = get_logger("learning.engine")

class LearningEngine:
    def __init__(self):
        self.user_model = get_user_model()
        self.semantic = get_semantic_memory()

    async def process_feedback(self, text: str) -> Optional[Dict[str, Any]]:
        clean = text.lower().strip()

        # Direct explicit feedback learning patterns
        if "don't" in clean or "never" in clean or "stop" in clean:
            if "long explanation" in clean or "verbose" in clean:
                self.user_model.record_preference("response_length", "concise", confidence=0.95, source="explicit_feedback")
                await get_event_bus().publish("learning.lesson_created", {"lesson": "User prefers concise explanations"}, source="learning_engine")
                return {"type": "preference", "key": "response_length", "value": "concise"}

        if "i prefer" in clean or "i always use" in clean:
            if "openrouter" in clean:
                self.user_model.record_preference("preferred_llm_provider", "openrouter", confidence=0.95, source="explicit_feedback")
                self.semantic.store_fact("user", "prefers_provider", "openrouter", fact_type=SemanticType.PREFERENCE, confidence=0.95)
                await get_event_bus().publish("learning.lesson_created", {"lesson": "User prefers OpenRouter model provider"}, source="learning_engine")
                return {"type": "preference", "key": "preferred_llm_provider", "value": "openrouter"}

        return None

_learning_engine = LearningEngine()

def get_learning_engine() -> LearningEngine:
    return _learning_engine
