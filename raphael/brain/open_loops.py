"""
Open Loop Tracking System for Raphael AI Assistant.
Tracks unresolved topics, pending issues, and open discussion loops across sessions.
"""

import time
from typing import Dict, Any, List, Optional
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger

logger = get_logger("brain.open_loops")

class OpenLoopTracker:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._init_table()

    def _init_table(self):
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_loops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'open',
                    priority REAL DEFAULT 0.8,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    def create_loop(self, topic: str, priority: float = 0.8) -> int:
        now = time.time()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM open_loops WHERE topic = ?", (topic,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE open_loops SET priority = ?, updated_at = ? WHERE id = ?", (priority, now, row["id"]))
                conn.commit()
                return row["id"]
            else:
                cursor.execute(
                    "INSERT INTO open_loops (topic, status, priority, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (topic, "open", priority, now, now)
                )
                conn.commit()
                loop_id = cursor.lastrowid
                logger.info(f"Open Loop Created [ID: {loop_id}]: '{topic}' (Priority: {priority})")
                return loop_id

    def list_open_loops(self) -> List[Dict[str, Any]]:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM open_loops WHERE status = 'open' ORDER BY priority DESC, updated_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def close_loop(self, topic: str) -> None:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE open_loops SET status = 'resolved', updated_at = ? WHERE topic = ?", (time.time(), topic))
            conn.commit()
            logger.info(f"Open Loop Resolved: '{topic}'")

_open_loop_tracker = OpenLoopTracker()

def get_open_loop_tracker() -> OpenLoopTracker:
    return _open_loop_tracker
