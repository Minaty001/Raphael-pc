"""
Routine Engine for Raphael AI Assistant.
Observes application usage sequences over time to detect daily routines.
"""

import time
from typing import Dict, Any, List, Optional
from raphael.memory.long_term import get_long_term_memory
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger

logger = get_logger("proactive.routine")

class RoutineEngine:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._init_table()

    def _init_table(self):
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    sequence TEXT NOT NULL,
                    confidence REAL DEFAULT 0.7,
                    occurrence_count INTEGER DEFAULT 1,
                    last_seen REAL NOT NULL
                )
            """)
            conn.commit()

    async def record_activity(self, app_name: str) -> Optional[Dict[str, Any]]:
        # Simple routine pattern recorder
        now = time.time()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM routines WHERE name = ?", (f"routine_{app_name}",))
            row = cursor.fetchone()
            if row:
                count = row["occurrence_count"] + 1
                conf = min(0.95, row["confidence"] + 0.05)
                cursor.execute(
                    "UPDATE routines SET occurrence_count = ?, confidence = ?, last_seen = ? WHERE name = ?",
                    (count, conf, now, f"routine_{app_name}")
                )
                conn.commit()
                if count >= 3:
                    routine = {"name": f"Daily {app_name} usage", "confidence": conf, "count": count}
                    await get_event_bus().publish("routine.detected", routine, source="routine_engine")
                    return routine
            else:
                cursor.execute(
                    "INSERT INTO routines (name, sequence, confidence, occurrence_count, last_seen) VALUES (?, ?, ?, ?, ?)",
                    (f"routine_{app_name}", app_name, 0.7, 1, now)
                )
                conn.commit()
        return None

_routine_engine = RoutineEngine()

def get_routine_engine() -> RoutineEngine:
    return _routine_engine
