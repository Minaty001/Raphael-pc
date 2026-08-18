"""
Goal Engine for Raphael AI Assistant.
Tracks active long-term goals and evaluates decisions against user objectives.
"""

import time
import json
from typing import Dict, Any, List, Optional
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus

logger = get_logger("brain.goals")

class GoalEngine:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._init_table()

    def _init_table(self):
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    progress REAL DEFAULT 0.0,
                    target_date REAL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def create_goal(self, title: str, target_date: Optional[float] = None) -> int:
        now = time.time()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO goals (title, status, progress, target_date, created_at) VALUES (?, ?, ?, ?, ?)",
                (title, "active", 0.0, target_date, now)
            )
            conn.commit()
            goal_id = cursor.lastrowid
            logger.info(f"Created New Goal [ID: {goal_id}]: '{title}'")
            return goal_id

    def list_active_goals(self) -> List[Dict[str, Any]]:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM goals WHERE status = 'active' ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def update_progress(self, goal_id: int, progress: float, status: str = "active") -> None:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE goals SET progress = ?, status = ? WHERE id = ?",
                (progress, status, goal_id)
            )
            conn.commit()
            logger.info(f"Updated Goal [ID: {goal_id}] Progress: {progress*100:.0f}% ({status})")

_goal_engine = GoalEngine()

def get_goal_engine() -> GoalEngine:
    return _goal_engine
