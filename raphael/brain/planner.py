"""
Planner for Raphael AI Assistant.
Decomposes complex natural language instructions into actionable execution steps.
"""

from typing import List, Dict, Any, Optional

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
    def create_plan(self, prompt: str) -> List[PlanStep]:
        clean = prompt.lower().strip()
        steps = []

        # Example multi-step pattern detection
        if "open chrome" in clean and "search" in clean:
            # Extract query
            query = "weather"
            if "search for" in clean:
                query = clean.split("search for")[-1].strip().split("and")[0].strip()
            
            steps.append(PlanStep(1, "open_application", {"app_name": "chrome"}, "Open Chrome application"))
            steps.append(PlanStep(2, "search_web", {"query": query}, f"Search web for '{query}'"))
        
        elif "take screenshot" in clean and "save" in clean:
            steps.append(PlanStep(1, "take_screenshot", {}, "Capture screen screenshot"))
            steps.append(PlanStep(2, "system_info", {}, "Fetch system metrics"))

        return steps

_planner_instance = Planner()

def get_planner() -> Planner:
    return _planner_instance
