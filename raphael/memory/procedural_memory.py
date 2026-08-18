"""
L4 Procedural Memory System for Raphael AI Assistant.
Learns reusable workflow procedures and step-by-step skill execution plans.
"""

import time
import json
import sqlite3
from typing import Dict, Any, List, Optional
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger

logger = get_logger("memory.procedural")

class ProceduralMemory:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._init_table()

    def _init_table(self):
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS procedures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    trigger_phrase TEXT NOT NULL,
                    steps TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.8,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    def save_procedure(
        self,
        name: str,
        trigger_phrase: str,
        steps: List[Dict[str, Any]],
        confidence: float = 0.8
    ) -> int:
        steps_json = json.dumps(steps)
        now = time.time()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, version FROM procedures WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                proc_id = row["id"]
                new_ver = row["version"] + 1
                cursor.execute(
                    "UPDATE procedures SET trigger_phrase = ?, steps = ?, version = ?, confidence = ?, updated_at = ? WHERE id = ?",
                    (trigger_phrase, steps_json, new_ver, confidence, now, proc_id)
                )
                conn.commit()
                logger.info(f"Updated Procedure '{name}' to v{new_ver}")
                return proc_id
            else:
                cursor.execute(
                    "INSERT INTO procedures (name, trigger_phrase, steps, version, confidence, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, trigger_phrase, steps_json, 1, confidence, now, now)
                )
                conn.commit()
                logger.info(f"Created New Procedure '{name}' v1")
                return cursor.lastrowid

    def get_procedure(self, name_or_trigger: str) -> Optional[Dict[str, Any]]:
        clean = name_or_trigger.lower().strip()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM procedures WHERE LOWER(name) = ? OR LOWER(trigger_phrase) LIKE ?",
                (clean, f"%{clean}%")
            )
            row = cursor.fetchone()
            if row:
                res = dict(row)
                res["steps"] = json.loads(res["steps"])
                return res
            return None

    def record_outcome(self, name: str, success: bool) -> None:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            if success:
                cursor.execute("UPDATE procedures SET success_count = success_count + 1 WHERE name = ?", (name,))
            else:
                cursor.execute("UPDATE procedures SET failure_count = failure_count + 1 WHERE name = ?", (name,))
            conn.commit()

_procedural_memory = ProceduralMemory()

def get_procedural_memory() -> ProceduralMemory:
    return _procedural_memory
