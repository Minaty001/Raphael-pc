"""
FIX 0 — Database / migration robustness.

Proves the `open_loops` table migration guard in raphael/brain/open_loops.py
(and raphael/memory/long_term.py) correctly adds the `updated_at` column even
when an OLDER schema (without the column) already exists WITH data in it. This
is the exact scenario that previously raised `no such column: updated_at`.
"""

import os
import sqlite3
import tempfile

from raphael.memory.long_term import LongTermMemory
from raphael.brain.open_loops import OpenLoopTracker


def _seed_legacy_open_loops(db_path: str):
    """Create an open_loops table WITHOUT updated_at, then insert rows."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE open_loops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'open',
            priority REAL DEFAULT 0.8,
            created_at REAL NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO open_loops (topic, created_at) VALUES (?, ?)",
        ("legacy topic A", 1.0),
    )
    conn.commit()
    conn.close()


def test_long_term_migration_adds_updated_at_on_populated_table():
    d = tempfile.mkdtemp()
    db_path = os.path.join(d, "memory.db")
    _seed_legacy_open_loops(db_path)

    # Patch the data dir so LongTermMemory uses our seeded db.
    import raphael.core.configuration as cfg_mod

    orig = cfg_mod.get_default_data_dir
    cfg_mod.get_default_data_dir = lambda: d  # type: ignore
    try:
        # Instantiate fresh (bypass singleton cache via new module-level store
        # by re-importing a local instance pointing at the same path).
        ltm = LongTermMemory.__new__(LongTermMemory)
        ltm.db_path = db_path
        ltm._init_db()
        conn = sqlite3.connect(db_path)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(open_loops)").fetchall()]
        conn.close()
        assert "updated_at" in cols, f"migration failed, columns={cols}"
    finally:
        cfg_mod.get_default_data_dir = orig  # type: ignore


def test_open_loop_tracker_works_on_migrated_schema():
    d = tempfile.mkdtemp()
    db_path = os.path.join(d, "memory.db")
    _seed_legacy_open_loops(db_path)

    tracker = OpenLoopTracker.__new__(OpenLoopTracker)
    # Manually point at the seeded db and run its init (the migration guard).
    from raphael.memory.long_term import LongTermMemory

    ltm = LongTermMemory.__new__(LongTermMemory)
    ltm.db_path = db_path
    ltm._init_db()
    tracker.ltm = ltm
    tracker._init_table()

    # Should not raise "no such column: updated_at" — this was the bug.
    tid = tracker.create_loop("new topic after migration", 0.9)
    assert isinstance(tid, int)
    loops = tracker.list_open_loops()
    assert any(l["topic"] == "new topic after migration" for l in loops)
    # Legacy row preserved.
    assert any(l["topic"] == "legacy topic A" for l in loops)
