"""
Cognitive Runtime Orchestrator for Raphael AI Assistant.
Orchestrates the central Raphael Cognitive Loop:
Observe -> Understand -> Remember -> Reason -> Decide -> Act -> Observe Result -> Evaluate -> Store Experience -> Reflect -> Update Memory.
"""

import time
import asyncio
from typing import Dict, Any, Optional
from raphael.perception.unified_perception import get_unified_perception
from raphael.memory.memory_manager import get_memory_manager
from raphael.memory.working_memory import get_working_memory
from raphael.brain.attention_manager import get_attention_manager
from raphael.brain.reasoning import get_reasoning_engine
from raphael.brain.goals import get_goal_engine
from raphael.brain.open_loops import get_open_loop_tracker
from raphael.learning.learning_engine import get_learning_engine
from raphael.learning.reflection_engine import get_reflection_engine
from raphael.proactive.proactive_engine import get_proactive_engine
from raphael.proactive.contextual_reminders import get_contextual_reminders
from raphael.core.state_manager import get_state_manager
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger

logger = get_logger("brain.cognitive_runtime")

class CognitiveRuntime:
    def __init__(self):
        self.perception = get_unified_perception()
        self.memory = get_memory_manager()
        self.working_memory = get_working_memory()
        self.attention = get_attention_manager()
        self.reasoning = get_reasoning_engine()
        self.goals = get_goal_engine()
        self.open_loops = get_open_loop_tracker()
        self.learning = get_learning_engine()
        self.reflection = get_reflection_engine()
        self.proactive = get_proactive_engine()
        self.reminders = get_contextual_reminders()

    async def execute_cognitive_cycle(self, user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a single step of the Raphael Cognitive Loop.
        """
        start_time = time.time()

        # 1. PERCEIVE
        observation = await self.perception.observe_environment()
        payload = observation.get("payload", {})
        app = payload.get("active_app", "")
        window = payload.get("window_title", "")

        # 2. INTERPRET & CONTEXTUALIZE
        self.working_memory.update_screen_state(payload)
        
        # Check contextual reminders
        await self.reminders.check_context_triggers(app, window)

        # 3. RETRIEVE MEMORY
        retrieved_memory = self.memory.hybrid_retrieve(user_input or app)

        # 4. REASON & DECIDE
        if user_input:
            # Learn from user input feedback if present
            await self.learning.process_feedback(user_input)

            # Core reasoning execution
            reasoning_res = await self.reasoning.process_user_input(user_input)
            
            # 5. ACT & OBSERVE RESULT
            tool_res = reasoning_res.get("tool_result")
            if tool_res:
                # 6. REFLECT & UPDATE MEMORY
                await self.reflection.reflect_on_task(tool_res.get("action", "task"), tool_res, user_input)

            return reasoning_res
        else:
            # Idle/Background proactive check
            proactive_res = await self.proactive.evaluate_proactive_opportunity(self.working_memory.get_summary())
            return {
                "observation": observation,
                "proactive_suggestion": proactive_res,
                "cycle_duration_ms": (time.time() - start_time) * 1000
            }

_cognitive_runtime = CognitiveRuntime()

def get_cognitive_runtime() -> CognitiveRuntime:
    return _cognitive_runtime
