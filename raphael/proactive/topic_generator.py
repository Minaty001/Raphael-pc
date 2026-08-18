"""
Topic Generator for Raphael v3.
Creates proactive conversation topics from project activity, screen state, and unfinished goals.
"""

from typing import List, Dict, Any
from raphael.memory.working_memory import get_working_memory
from raphael.brain.goals import get_goal_engine
from raphael.brain.open_loops import get_open_loop_tracker
from raphael.core.logging import get_logger

logger = get_logger("proactive.topics")

class TopicGenerator:
    def __init__(self):
        self.working_mem = get_working_memory()
        self.goals = get_goal_engine()
        self.open_loops = get_open_loop_tracker()

    def generate_candidate_topics(self) -> List[Dict[str, Any]]:
        """
        Generates candidate proactive discussion topics.
        """
        topics = []
        
        # Open loops topics
        loops = self.open_loops.list_open_loops()
        for loop in loops:
            topics.append({
                "title": f"Unresolved Topic: {loop['topic']}",
                "source": "open_loop",
                "priority": loop.get("priority", 0.7),
                "prompt": f"Regarding '{loop['topic']}', would you like to continue working on this?"
            })

        # Active goal topics
        active_goals = self.goals.list_active_goals()
        for goal in active_goals:
            topics.append({
                "title": f"Goal Objective: {goal['title']}",
                "source": "goal_engine",
                "priority": goal.get("priority", 0.6),
                "prompt": f"Should we make progress on goal '{goal['title']}' today?"
            })

        topics.sort(key=lambda x: x["priority"], reverse=True)
        return topics

_topic_generator = TopicGenerator()

def get_topic_generator() -> TopicGenerator:
    return _topic_generator
