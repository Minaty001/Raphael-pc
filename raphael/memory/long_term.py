"""
SQLite Persistent Long-Term Memory Store for Raphael v3.
Manages all 20 core relational database tables and schema migrations.
"""

import sqlite3
import json
import os
import time
from typing import Dict, Any, List, Optional
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("memory.long_term")

class LongTermMemory:
    def __init__(self):
        config = get_config()
        data_dir = config.get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "memory.db")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """
        Initializes and migrates the 20 official Raphael v3 relational database tables.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check if old memories schema exists and migrate if needed
            cursor.execute("PRAGMA table_info(memories)")
            columns = [col["name"] for col in cursor.fetchall()]
            if columns and "subject" not in columns:
                logger.info("Migrating old memories table schema to Raphael v3 semantic memories schema...")
                cursor.execute("DROP TABLE memories")

            # 1. users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    created_at REAL NOT NULL
                )
            """)

            # 2. sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_key TEXT UNIQUE NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL
                )
            """)

            # 3. messages
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT,
                    timestamp REAL NOT NULL
                )
            """)

            # 4. memories (L3 Semantic Memory)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_value TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    evidence_count INTEGER NOT NULL DEFAULT 1,
                    source TEXT,
                    provenance TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)

            # 5. memory_links
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_memory_id INTEGER NOT NULL,
                    target_memory_id INTEGER NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL DEFAULT 1.0
                )
            """)

            # 6. episodes (L2 Episodic Memory)
            # Owned by raphael/memory/episodic_memory.py. We declare a compatible
            # schema here so the table exists regardless of import order, but the
            # summary-based schema is authoritative (FIX 0 — avoid dual schema).
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
            # Upgrade any legacy action/details-based episodes table.
            cols = [c["name"] for c in cursor.execute("PRAGMA table_info(episodes)").fetchall()]
            if "action" in cols and "summary" not in cols:
                logger.info("Migrating episodes table -> episodic schema")
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

            # 7. procedures (L4 Procedural Memory)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS procedures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    steps_json TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    created_at REAL NOT NULL
                )
            """)

            # 8. skills
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    trigger_phrase TEXT NOT NULL,
                    version TEXT DEFAULT 'v1',
                    procedure_json TEXT NOT NULL,
                    success_rate REAL DEFAULT 1.0,
                    created_at REAL NOT NULL
                )
            """)

            # 9. preferences (L5 User Model)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value_json TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    evidence_count INTEGER DEFAULT 1,
                    updated_at REAL NOT NULL
                )
            """)

            # 10. goals
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    priority REAL DEFAULT 0.5,
                    progress REAL DEFAULT 0.0,
                    project TEXT,
                    created_at REAL NOT NULL
                )
            """)

            # 11. tasks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER,
                    description TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at REAL NOT NULL
                )
            """)

            # 12. routines
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    pattern_json TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    confirmed_by_user INTEGER DEFAULT 0,
                    created_at REAL NOT NULL
                )
            """)

            # 13. open_loops
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS open_loops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'open',
                    priority REAL DEFAULT 0.5,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            # Migration guard: the same table is also declared in
            # raphael/brain/open_loops.py. Ensure the `updated_at` column exists
            # regardless of which module created the table first (FIX 0).
            cols = [c["name"] for c in cursor.execute("PRAGMA table_info(open_loops)").fetchall()]
            if "updated_at" not in cols:
                logger.info("Migrating open_loops: adding updated_at column")
                cursor.execute("ALTER TABLE open_loops ADD COLUMN updated_at REAL NOT NULL DEFAULT 0")

            # 14. events
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)

            # 15. tool_calls
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    args_json TEXT NOT NULL,
                    result_json TEXT,
                    status TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)

            # 16. learning_records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    created_at REAL NOT NULL
                )
            """)

            # 17. reflections
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    lesson TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)

            # 18. topics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    relevance REAL DEFAULT 0.5,
                    created_at REAL NOT NULL
                )
            """)

            # 19. questions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    context TEXT,
                    status TEXT DEFAULT 'unasked',
                    created_at REAL NOT NULL
                )
            """)

            # 20. reminders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    trigger_context TEXT,
                    due_timestamp REAL,
                    status TEXT DEFAULT 'pending',
                    created_at REAL NOT NULL
                )
            """)

            conn.commit()

    def list_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

_long_term_memory = LongTermMemory()

def get_long_term_memory() -> LongTermMemory:
    return _long_term_memory
