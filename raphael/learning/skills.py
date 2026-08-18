"""
Skill Acquisition System for Raphael AI Assistant.
Encapsulates procedural skill templates and workflow sequences.
"""

from typing import Dict, Any, List
from raphael.memory.procedural_memory import get_procedural_memory
from raphael.core.logging import get_logger

logger = get_logger("learning.skills")

class SkillManager:
    def __init__(self):
        self.procedural = get_procedural_memory()
        self._bootstrap_default_skills()

    def _bootstrap_default_skills(self):
        # Default skill: Start Raphael Development
        dev_steps = [
            {"step": 1, "tool": "system_info", "description": "Check system metrics"},
            {"step": 2, "tool": "find_file", "args": {"query": "raphael"}, "description": "Locate project files"}
        ]
        self.procedural.save_procedure("start_raphael_development", "start raphael dev", dev_steps)

    def learn_new_skill(self, name: str, trigger_phrase: str, steps: List[Dict[str, Any]]) -> int:
        logger.info(f"New Skill Learned: '{name}' (Trigger: '{trigger_phrase}')")
        return self.procedural.save_procedure(name, trigger_phrase, steps)

_skill_manager = SkillManager()

def get_skill_manager() -> SkillManager:
    return _skill_manager
