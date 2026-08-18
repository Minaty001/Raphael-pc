"""
User Model System for Raphael AI Assistant.
Maintains user preferences, habits, frequent tasks, and evidence-weighted profiles.
"""

import time
import json
import sqlite3
from typing import Dict, Any, List, Optional
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger

logger = get_logger("memory.user_model")

class UserModel:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._init_table()

    def _init_table(self):
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    trait_key TEXT PRIMARY KEY,
                    trait_value TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    evidence_count INTEGER DEFAULT 1,
                    source TEXT DEFAULT 'observation',
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()

    def record_preference(self, key: str, value: Any, confidence: float = 0.7, source: str = "observation") -> None:
        val_str = json.dumps(value) if not isinstance(value, str) else value
        now = time.time()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT confidence, evidence_count FROM user_profile WHERE trait_key = ?", (key,))
            row = cursor.fetchone()
            if row:
                new_count = row["evidence_count"] + 1
                new_conf = min(0.99, row["confidence"] + 0.05)
                cursor.execute(
                    "UPDATE user_profile SET trait_value = ?, confidence = ?, evidence_count = ?, source = ?, updated_at = ? WHERE trait_key = ?",
                    (val_str, new_conf, new_count, source, now, key)
                )
                logger.info(f"User Model updated preference '{key}' -> '{val_str}' (Evidence count: {new_count}, Conf: {new_conf:.2f})")
            else:
                cursor.execute(
                    "INSERT INTO user_profile (trait_key, trait_value, confidence, evidence_count, source, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (key, val_str, confidence, 1, source, now)
                )
                logger.info(f"User Model new preference recorded '{key}' -> '{val_str}' (Conf: {confidence:.2f})")
            conn.commit()

    def get_profile(self) -> Dict[str, Any]:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profile ORDER BY confidence DESC")
            profile = {}
            for row in cursor.fetchall():
                key = row["trait_key"]
                val = row["trait_value"]
                try:
                    val = json.loads(val)
                except Exception:
                    pass
                profile[key] = {
                    "value": val,
                    "confidence": row["confidence"],
                    "evidence_count": row["evidence_count"],
                    "source": row["source"]
                }
            return profile

_user_model = UserModel()

def get_user_model() -> UserModel:
    return _user_model
