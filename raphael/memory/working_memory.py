"""
L0 Working Memory for Raphael AI Assistant.
Maintains short-lived context (active task, current goal, recent screen state, unresolved questions).
"""

import time
from typing import Dict, Any, List, Optional
from raphael.core.logging import get_logger

logger = get_logger("memory.working")

class WorkingMemory:
    def __init__(self):
        self.active_goal: Optional[str] = "Build Raphael PC v2 Cognitive Assistant"
        self.current_plan: List[Dict[str, Any]] = []
        self.recent_screen_state: Optional[Dict[str, Any]] = None
        self.last_action: Optional[Dict[str, Any]] = None
        self.unresolved_questions: List[str] = []
        self.recent_observations: List[Dict[str, Any]] = []

    def update_screen_state(self, state: Dict[str, Any]) -> None:
        self.recent_screen_state = state

    def set_active_goal(self, goal: str) -> None:
        logger.info(f"Working Memory Active Goal updated: '{goal}'")
        self.active_goal = goal

    def add_unresolved_question(self, question: str) -> None:
        if question not in self.unresolved_questions:
            self.unresolved_questions.append(question)

    def resolve_question(self, question: str) -> None:
        if question in self.unresolved_questions:
            self.unresolved_questions.remove(question)

    def add_observation(self, obs: Dict[str, Any]) -> None:
        self.recent_observations.append(obs)
        if len(self.recent_observations) > 20:
            self.recent_observations.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "active_goal": self.active_goal,
            "current_plan_steps": len(self.current_plan),
            "last_action": self.last_action,
            "recent_screen": self.recent_screen_state,
            "unresolved_questions": list(self.unresolved_questions),
            "recent_observations_count": len(self.recent_observations)
        }

_working_memory = WorkingMemory()

def get_working_memory() -> WorkingMemory:
    return _working_memory
