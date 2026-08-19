"""
Planner for Raphael AI Assistant.
Decomposes complex natural language instructions into actionable execution steps.

ROADMAP L8 (Planning): the planner first tries fast, deterministic pattern
matches for common multi-step requests, then falls back to LLM-driven
decomposition for novel requests it cannot pattern-match. Any LLM failure
degrades gracefully to an empty plan (the reasoning engine then handles the
request as a normal conversational turn).
"""

import json
import re
from typing import List, Dict, Any, Optional, Awaitable

from raphael.core.logging import get_logger

logger = get_logger("brain.planner")


class PlanStep:
    def __init__(self, step_id: int, tool_name: str, args: Dict[str, Any], description: str):
        self.step_id = step_id
        self.tool_name = tool_name
        self.args = args
        self.description = description
        self.status = "pending"
        self.result: Optional[Any] = None
        self.error: Optional[str] = None


class Planner:
    async def create_plan(self, prompt: str) -> List[PlanStep]:
        """Decompose `prompt` into ordered PlanSteps.

        Strategy: deterministic patterns first (offline, instant, reliable);
        otherwise ask the LLM to decompose the request using the available tool
        registry. Always returns a list (possibly empty).
        """
        clean = prompt.lower().strip()

        # 1) Deterministic pattern matches (fast path).
        steps = self._pattern_plan(clean)
        if steps:
            return steps

        # 2) LLM-driven decomposition for novel multi-step requests.
        try:
            return await self._llm_plan(prompt)
        except Exception as e:
            logger.warning(f"LLM planning failed, returning empty plan: {e}")
            return []

    def _pattern_plan(self, clean: str) -> List[PlanStep]:
        steps: List[PlanStep] = []

        if "open chrome" in clean and "search" in clean:
            query = "weather"
            if "search for" in clean:
                query = clean.split("search for")[-1].strip().split("and")[0].strip()
            steps.append(PlanStep(1, "open_application", {"app_name": "chrome"}, "Open Chrome application"))
            steps.append(PlanStep(2, "search_web", {"query": query}, f"Search web for '{query}'"))

        elif "take screenshot" in clean and "save" in clean:
            steps.append(PlanStep(1, "take_screenshot", {}, "Capture screen screenshot"))
            steps.append(PlanStep(2, "system_info", {}, "Fetch system metrics"))

        return steps

    async def _llm_plan(self, prompt: str) -> List[PlanStep]:
        from raphael.brain.llm_router import get_llm_router
        from raphael.tools.registry import get_tool_registry

        registry = get_tool_registry()
        tools = registry.list_tools()
        if not tools:
            return []

        tool_catalog = "\n".join(
            f"- {t['name']}({', '.join(t.get('parameters', []))}): {t['description']}"
            for t in tools
        )

        system = (
            "You are the planning module of Raphael, an AI desktop assistant. "
            "Given a user request, decompose it into a short ordered list of tool "
            "calls using ONLY the tools listed below. Respond with ONE JSON array "
            "of objects, each with keys: tool_name (exact tool name from the list), "
            "args (object with parameter names from the tool signature), and "
            "description (one short sentence). If the request is a single simple "
            "action or just conversation, return an empty array []."
        )
        user = f"AVAILABLE TOOLS:\n{tool_catalog}\n\nUSER REQUEST: {prompt}"

        router = get_llm_router()
        raw = await router.chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
        parsed = _extract_json_array(raw)
        if parsed is None:
            logger.warning("LLM plan response was not valid JSON; returning empty plan")
            return []

        valid_names = {t["name"] for t in tools}
        steps: List[PlanStep] = []
        i = 1
        for item in parsed:
            name = item.get("tool_name")
            if name not in valid_names:
                logger.warning(f"LLM proposed unknown tool '{name}'; skipping step")
                continue
            args = item.get("args") or {}
            if not isinstance(args, dict):
                args = {}
            desc = item.get("description") or f"Step {i}: {name}"
            steps.append(PlanStep(i, name, args, desc))
            i += 1

        return steps


def _extract_json_array(text: str) -> Optional[List[Any]]:
    """Robustly extract a JSON array from an LLM response.

    Handles code fences (```json ... ```) and prose wrapping. Returns None if no
    valid JSON array can be found.
    """
    if not text:
        return None
    # Strip common code fences.
    cleaned = re.sub(r"```(?:json)?\s*", "", text).strip()
    cleaned = cleaned.strip("`").strip()

    # Try the whole string first.
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, list):
            return obj
    except json.JSONDecodeError:
        pass

    # Fall back: locate the first '[' ... last ']' span.
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(cleaned[start : end + 1])
            if isinstance(obj, list):
                return obj
        except json.JSONDecodeError:
            pass

    return None


_planner_instance = Planner()


def get_planner() -> Planner:
    return _planner_instance
