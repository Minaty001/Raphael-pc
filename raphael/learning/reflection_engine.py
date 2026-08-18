"""
Self-Reflection Engine for Raphael AI Assistant.
Evaluates task outcomes after execution, extracts lessons, and updates strategies.
"""

import time
import asyncio
from typing import Dict, Any, Optional
from raphael.core.event_bus import get_event_bus
from raphael.memory.episodic_memory import get_episodic_memory
from raphael.core.logging import get_logger

logger = get_logger("learning.reflection")

class ReflectionEngine:
    async def reflect_on_task(self, task_name: str, tool_res: Dict[str, Any], user_request: str) -> Dict[str, Any]:
        bus = get_event_bus()
        await bus.publish("reflection.started", {"task": task_name}, source="reflection_engine")

        status = tool_res.get("status", "unknown")
        duration = tool_res.get("duration_ms", 0)
        error = tool_res.get("error")

        if status == "success":
            lesson = f"Task '{task_name}' executed cleanly in {duration:.1f}ms."
            importance = 0.6
        else:
            lesson = f"Task '{task_name}' failed ({error}). Need alternative strategy or parameter check."
            importance = 0.85

        # Record reflection in episodic memory
        episodic = get_episodic_memory()
        episodic.record_episode(
            summary=f"Reflection on {task_name}: {lesson}",
            category="reflection",
            importance=importance,
            confidence=0.9
        )

        reflection_res = {
            "task": task_name,
            "status": status,
            "lesson": lesson,
            "timestamp": time.time()
        }

        await bus.publish("reflection.completed", reflection_res, source="reflection_engine")
        logger.info(f"Self-Reflection Completed: {lesson}")
        return reflection_res

_reflection_engine = ReflectionEngine()

def get_reflection_engine() -> ReflectionEngine:
    return _reflection_engine
