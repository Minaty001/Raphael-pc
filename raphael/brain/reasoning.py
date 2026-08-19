"""
Reasoning & Cognitive Execution Engine for Raphael v3.
Orchestrates state transitions, structured reasoning state, metacognition, intent recognition, tool execution, and action verification.
"""

import time
from typing import Dict, Any, Optional, List
from raphael.core.state_manager import get_state_manager, AssistantState
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger
from raphael.brain.intent import get_intent_engine
from raphael.brain.llm_router import get_llm_router
from raphael.brain.planner import get_planner, PlanStep
from raphael.brain.meta_cognition import get_meta_cognition
from raphael.brain.action_verifier import get_action_verifier
from raphael.memory.memory_manager import get_memory_manager
from raphael.memory.working_memory import get_working_memory
from raphael.learning.learning_engine import get_learning_engine
from raphael.learning.reflection_engine import get_reflection_engine
from raphael.tools.registry import get_tool_registry

logger = get_logger("brain.reasoning")

class PlanResult:
    """Structured outcome of executing a multi-step plan (ROADMAP L11)."""
    def __init__(self):
        self.steps_total = 0
        self.steps_completed = 0
        self.steps_failed = 0
        self.aborted = False
        self.step_results: List[Dict[str, Any]] = []
        self.message = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps_total": self.steps_total,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "aborted": self.aborted,
            "step_results": self.step_results,
            "message": self.message,
        }


class ReasoningEngine:
    def __init__(self):
        self.state_mgr = get_state_manager()
        self.event_bus = get_event_bus()
        self.intent_engine = get_intent_engine()
        self.llm_router = get_llm_router()
        self.planner = get_planner()
        self.meta_cognition = get_meta_cognition()
        self.verifier = get_action_verifier()
        self.memory_mgr = get_memory_manager()
        self.working_mem = get_working_memory()
        self.learning_engine = get_learning_engine()
        self.reflection_engine = get_reflection_engine()
        self.tool_registry = get_tool_registry()

    async def execute_plan(self, plan: List[PlanStep], user_request: str) -> PlanResult:
        """Execute a plan step-by-step with per-step verification + recovery.

        ROADMAP L11 Agent Loop: ACT -> OBSERVE -> VERIFY -> (RECOVER) -> next.
        On a step failure we retry once; if it still fails the plan aborts and
        we report honestly which steps completed and which did not (no silent
        success).
        """
        result = PlanResult()
        result.steps_total = len(plan)
        await self.state_mgr.set_state(AssistantState.EXECUTING, {"plan_steps": len(plan)})

        for step in plan:
            step.status = "running"
            await self.event_bus.publish({
                "type": "plan.step.start",
                "step_id": step.step_id,
                "tool": step.tool_name,
                "description": step.description,
            })

            tool_res = await self.tool_registry.execute_tool(step.tool_name, step.args or {})
            verified = tool_res.get("verification", {}).get("verified")
            ok = tool_res.get("status") == "success" and verified is not False

            # Recovery: one retry on failure / unverified outcome.
            if not ok:
                logger.warning(f"Plan step {step.step_id} ({step.tool_name}) failed/Unverified; retrying once")
                tool_res = await self.tool_registry.execute_tool(step.tool_name, step.args or {})
                verified = tool_res.get("verification", {}).get("verified")
                ok = tool_res.get("status") == "success" and verified is not False

            step.result = tool_res
            if ok:
                step.status = "completed"
                result.steps_completed += 1
                result.step_results.append({
                    "step_id": step.step_id, "status": "completed",
                    "tool": step.tool_name, "result": tool_res.get("result"),
                })
                await self.event_bus.publish({
                    "type": "plan.step.completed",
                    "step_id": step.step_id, "tool": step.tool_name,
                })
            else:
                step.status = "failed"
                step.error = tool_res.get("error") or "step unverified"
                result.steps_failed += 1
                result.step_results.append({
                    "step_id": step.step_id, "status": "failed",
                    "tool": step.tool_name, "error": step.error,
                })
                await self.event_bus.publish({
                    "type": "plan.step.failed",
                    "step_id": step.step_id, "tool": step.tool_name,
                    "error": step.error,
                })
                # Abort the plan on a hard failure (no silent partial success).
                result.aborted = True
                result.message = (
                    f"Plan aborted at step {step.step_id} ({step.tool_name}): {step.error}. "
                    f"{result.steps_completed}/{result.steps_total} steps completed."
                )
                break

        if not result.aborted:
            result.message = (
                f"Plan completed: all {result.steps_total} steps executed successfully."
            )
        await self.reflection_engine.reflect_on_task("plan_execution", result.to_dict(), user_request)
        return result

    async def process_user_input(self, text: str) -> Dict[str, Any]:
        """
        Full Raphael v3 Cognitive Processing Loop:
        IDLE -> UNDERSTANDING -> RETRIEVING_MEMORY -> THINKING -> PLANNING -> EXECUTING -> VERIFYING -> REFLECTING -> SPEAKING -> IDLE
        """
        start_time = time.time()
        
        # 1. UNDERSTANDING
        await self.state_mgr.set_state(AssistantState.UNDERSTANDING, {"input": text})
        intent_res = self.intent_engine.classify_intent(text)
        
        # 2. RETRIEVING_MEMORY
        await self.state_mgr.set_state(AssistantState.RETRIEVING_MEMORY, {"query": text})
        memory_context = self.memory_mgr.hybrid_retrieve(text)
        
        # 3. THINKING & METACOGNITION
        await self.state_mgr.set_state(AssistantState.THINKING)
        metacog_res = self.meta_cognition.evaluate_uncertainty(text, memory_context["semantic_facts"])

        # 4. INTENT / PLAN SELECTION
        tool_result = None
        plan = None
        response_text = ""

        if intent_res["matched"] and intent_res["confidence"] > 0.8:
            tool_name = intent_res["tool_name"]
            tool_args = intent_res["tool_args"]
            
            # 5. EXECUTING
            await self.state_mgr.set_state(AssistantState.EXECUTING, {"tool": tool_name, "args": tool_args})
            tool_result = await self.tool_registry.execute_tool(tool_name, tool_args)
            
            # 6. VERIFYING
            await self.state_mgr.set_state(AssistantState.VERIFYING, {"tool": tool_name})
            verif_res = await self.verifier.verify_action(tool_name, tool_args, tool_result)
            tool_result["verified"] = verif_res["verified"]

            # Formulate response
            if tool_result.get("status") == "success":
                response_text = f"Executed {tool_name} successfully. Output: {tool_result.get('result')}"
            else:
                response_text = f"Action {tool_name} failed: {tool_result.get('error')}"
        else:
            # Multi-step intent: build a plan and EXECUTE it as a loop.
            await self.state_mgr.set_state(AssistantState.PLANNING)
            plan = self.planner.create_plan(text)

            if plan:
                plan_result = await self.execute_plan(plan, text)
                response_text = plan_result.message
                await self.state_mgr.set_state(AssistantState.SPEAKING, {"text": response_text})
                await self.event_bus.publish({
                    "type": "assistant.message",
                    "text": response_text,
                    "plan_result": plan_result.to_dict(),
                    "timestamp": time.time(),
                })
                await self.state_mgr.set_state(AssistantState.IDLE)
                return {
                    "text": response_text,
                    "intent": intent_res,
                    "tool_result": None,
                    "plan": [s.__dict__ for s in plan],
                    "plan_result": plan_result.to_dict(),
                    "metacognition": metacog_res,
                    "duration_ms": (time.time() - start_time) * 1000,
                }

            # No plannable structure: use the LLM for a conversational response.
            prompt = f"User Request: {text}\nContext: {memory_context['active_context']}\nMemories: {memory_context['relevant_memories']}"
            try:
                llm_res = await self.llm_router.chat([{"role": "user", "content": prompt}])
            except Exception as e:
                logger.error(f"LLM provider call failed: {e}")
                response_text = (
                    "I couldn't reach the LLM provider. If you're using Groq/OpenRouter, "
                    "check that your API key is valid and set (local .env file). "
                    f"(Provider error: {type(e).__name__})"
                )
                # Skip the rest of the cognitive loop on provider failure.
                await self.state_mgr.set_state(AssistantState.SPEAKING, {"text": response_text})
                await self.event_bus.publish({
                    "type": "assistant.message",
                    "text": response_text,
                    "tool_result": None,
                    "intent": intent_res,
                    "plan": None,
                    "metacognition": metacog_res,
                    "duration_ms": (time.time() - start_time) * 1000,
                })
                return {
                    "text": response_text,
                    "intent": intent_res,
                    "tool_result": None,
                    "plan": None,
                    "metacognition": metacog_res,
                    "duration_ms": (time.time() - start_time) * 1000,
                }
            response_text = llm_res if isinstance(llm_res, str) else llm_res.get("text", "I'm processing your request.")

        # 7. REFLECTING & LEARNING
        await self.state_mgr.set_state(AssistantState.REFLECTING)
        if tool_result:
            await self.reflection_engine.reflect_on_task(tool_result.get("action", "task"), tool_result, text)
        await self.learning_engine.process_feedback(text)

        # 8. SPEAKING
        await self.state_mgr.set_state(AssistantState.SPEAKING, {"text": response_text})
        
        # Publish completion event over event bus
        await self.event_bus.publish({
            "type": "assistant.message",
            "text": response_text,
            "tool_result": tool_result,
            "timestamp": time.time()
        })

        # Return to IDLE
        await self.state_mgr.set_state(AssistantState.IDLE)

        duration_ms = (time.time() - start_time) * 1000
        return {
            "text": response_text,
            "intent": intent_res,
            "tool_result": tool_result,
            "plan": plan,
            "metacognition": metacog_res,
            "duration_ms": duration_ms
        }

_reasoning_engine = ReasoningEngine()

def get_reasoning_engine() -> ReasoningEngine:
    return _reasoning_engine
