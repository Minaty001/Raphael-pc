"""
L2 Episodic Memory System for Raphael AI Assistant.
Stores timestamped experience episodes and tool interaction outcomes.
"""

import time
import json
import sqlite3
from typing import Dict, Any, List, Optional
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger

logger = get_logger("memory.episodic")

class EpisodicMemory:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._init_table()

    def _init_table(self):
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            # FIX 0: guarantee the canonical episodic schema exists. If a legacy
            # action/details-based `episodes` table was created by another module
            # first, rebuild it as the summary-based schema (dev DBs only).
            cursor.execute("PRAGMA table_info(episodes)")
            cols = [c["name"] for c in cursor.fetchall()]
            if "action" in cols:
                # Legacy action/details-based table from an earlier schema.
                # Rebuild as the canonical summary-based schema (dev DBs only).
                logger.info("Rebuilding legacy episodes table -> episodic schema")
                cursor.execute("ALTER TABLE episodes RENAME TO episodes_legacy_tmp")
                cursor.execute("""
                    CREATE TABLE episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        summary TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        entities TEXT,
                        importance REAL DEFAULT 0.7,
                        confidence REAL DEFAULT 0.9,
                        source TEXT DEFAULT 'user_interaction',
                        timestamp REAL NOT NULL
                    )
                """)
                cursor.execute(
                    "INSERT INTO episodes (id, timestamp) SELECT id, timestamp FROM episodes_legacy_tmp"
                )
                cursor.execute("DROP TABLE episodes_legacy_tmp")
            else:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS episodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        summary TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        entities TEXT,
                        importance REAL DEFAULT 0.7,
                        confidence REAL DEFAULT 0.9,
                        source TEXT DEFAULT 'user_interaction',
                        timestamp REAL NOT NULL
                    )
                """)
            conn.commit()

    def record_episode(
        self,
        summary: str,
        category: str = "general",
        entities: Optional[List[str]] = None,
        importance: float = 0.7,
        confidence: float = 0.9,
        source: str = "user_interaction"
    ) -> int:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO episodes (summary, category, entities, importance, confidence, source, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (summary, category, json.dumps(entities or []), importance, confidence, source, time.time())
            )
            conn.commit()
            logger.info(f"Recorded Episode [Importance: {importance:.2f}]: '{summary[:60]}...'")
            return cursor.lastrowid

    def retrieve_episodes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        clean_q = query.lower().strip()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM episodes WHERE LOWER(summary) LIKE ? ORDER BY importance DESC, timestamp DESC LIMIT ?",
                (f"%{clean_q}%", limit)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

_episodic_memory = EpisodicMemory()

def get_episodic_memory() -> EpisodicMemory:
    return _episodic_memory
