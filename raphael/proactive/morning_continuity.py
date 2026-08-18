"""
Morning Continuity Briefing Engine for Raphael v3.
Provides context restoration and continuity briefing on system startup or new daily sessions.
"""

from typing import Dict, Any
from raphael.brain.goals import get_goal_engine
from raphael.brain.open_loops import get_open_loop_tracker
from raphael.memory.user_model import get_user_model
from raphael.core.logging import get_logger

logger = get_logger("proactive.continuity")

class MorningContinuityEngine:
    def __init__(self):
        self.goals = get_goal_engine()
        self.open_loops = get_open_loop_tracker()
        self.user_model = get_user_model()

    def generate_morning_briefing(self) -> Dict[str, Any]:
        """
        Retrieves unfinished goals, open loops, and user preferences to build a daily continuity briefing.
        """
        active_goals = self.goals.list_active_goals()
        open_loops = self.open_loops.list_open_loops()
        user_profile = self.user_model.get_profile()

        briefing_text = "Good morning. "
        if active_goals:
            g_titles = ", ".join([g["title"] for g in active_goals[:2]])
            briefing_text += f"Active goals for today: {g_titles}. "
        if open_loops:
            l_topics = ", ".join([l["topic"] for l in open_loops[:2]])
            briefing_text += f"Open discussions pending: {l_topics}."

        logger.info(f"Generated morning continuity briefing: {briefing_text}")
        return {
            "briefing_text": briefing_text,
            "active_goals_count": len(active_goals),
            "open_loops_count": len(open_loops),
            "user_profile": user_profile
        }

_morning_continuity = MorningContinuityEngine()

def get_morning_continuity() -> MorningContinuityEngine:
    return _morning_continuity
