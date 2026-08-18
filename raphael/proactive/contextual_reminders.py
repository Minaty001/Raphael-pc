"""
Contextual Reminders Engine for Raphael AI Assistant.
Triggers reminders based on environmental context (e.g. active app opening, project matching).
"""

import time
from typing import Dict, Any, List, Optional
from raphael.core.event_bus import get_event_bus
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger

logger = get_logger("proactive.reminders")

class ContextualReminderEngine:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._init_table()

    def _init_table(self):
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contextual_reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    trigger_context TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def set_reminder(self, title: str, trigger_context: str) -> int:
        now = time.time()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO contextual_reminders (title, trigger_context, status, created_at) VALUES (?, ?, ?, ?)",
                (title, trigger_context.lower(), "pending", now)
            )
            conn.commit()
            reminder_id = cursor.lastrowid
            logger.info(f"Contextual Reminder Set [ID: {reminder_id}]: '{title}' on trigger '{trigger_context}'")
            return reminder_id

    async def check_context_triggers(self, current_app: str, window_title: str) -> List[Dict[str, Any]]:
        context_str = f"{current_app} {window_title}".lower()
        triggered = []
        
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contextual_reminders WHERE status = 'pending'")
            rows = cursor.fetchall()
            
            for row in rows:
                trig = row["trigger_context"]
                if trig in context_str:
                    rem_id = row["id"]
                    cursor.execute("UPDATE contextual_reminders SET status = 'triggered' WHERE id = ?", (rem_id,))
                    conn.commit()
                    
                    payload = {"id": rem_id, "title": row["title"], "trigger": trig}
                    triggered.append(payload)
                    await get_event_bus().publish("reminder.triggered", payload, source="contextual_reminders")
                    logger.info(f"Contextual Reminder Triggered: '{row['title']}'")

        return triggered

_contextual_reminders = ContextualReminderEngine()

def get_contextual_reminders() -> ContextualReminderEngine:
    return _contextual_reminders
