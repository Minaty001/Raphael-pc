"""
L3 Semantic Memory & Write Gate Engine for Raphael v3.
Manages durable facts, preferences, rules, beliefs, and constraints with write gating & confidence scores.
"""

from enum import Enum
import time
from typing import Dict, Any, List, Optional
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger

logger = get_logger("memory.semantic")

class SemanticType(str, Enum):
    FACT = "FACT"
    PREFERENCE = "PREFERENCE"
    BELIEF = "BELIEF"
    RULE = "RULE"
    CONSTRAINT = "CONSTRAINT"
    PROJECT_INFO = "PROJECT_INFO"
    USER_INFO = "USER_INFO"

class SemanticMemory:
    def __init__(self):
        self.ltm = get_long_term_memory()

    def store_fact(
        self,
        subject: str,
        predicate: str,
        object_value: str,
        fact_type: SemanticType = SemanticType.FACT,
        confidence: float = 1.0,
        source: str = "direct_input"
    ) -> Optional[int]:
        """
        Stores a semantic memory fact after passing through the Write Gate.
        Handles conflict resolution (Section 26) when new info conflicts with old.
        """
        if confidence < 0.5:
            logger.info(f"Write Gate REJECTED low confidence memory ({confidence}): {subject} {predicate} {object_value}")
            return None

        # Check if identical memory already exists
        existing = self.query_facts(subject, predicate)
        if existing:
            for old_fact in existing:
                if old_fact["object_value"] == object_value:
                    # Reinforce existing memory evidence count and return its ID
                    self._increment_evidence(old_fact["id"])
                    return old_fact["id"]
                else:
                    if confidence >= old_fact.get("confidence", 0.5):
                        # Supersede old conflicting belief
                        logger.info(f"Conflict Resolved: Replacing '{old_fact['object_value']}' with '{object_value}' for {subject}.{predicate}")
                        self.delete_fact_by_id(old_fact["id"])

        now = time.time()
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memories (
                    subject, predicate, object_value, memory_type,
                    confidence, evidence_count, source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            """, (subject, predicate, object_value, fact_type.value, confidence, source, now, now))
            conn.commit()
            fact_id = cursor.lastrowid
            logger.info(f"Stored L3 Semantic Memory [{fact_id}]: {subject} {predicate} {object_value} (conf={confidence})")
            return fact_id

    def query_facts(self, subject: Optional[str] = None, predicate: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            if subject and predicate:
                cursor.execute("SELECT * FROM memories WHERE subject=? AND predicate=?", (subject, predicate))
            elif subject:
                cursor.execute("SELECT * FROM memories WHERE subject=?", (subject,))
            elif predicate:
                cursor.execute("SELECT * FROM memories WHERE predicate=?", (predicate,))
            else:
                cursor.execute("SELECT * FROM memories ORDER BY confidence DESC LIMIT 100")
            return [dict(r) for r in cursor.fetchall()]

    def delete_matching_facts(self, keyword: str) -> int:
        kw = f"%{keyword.lower()}%"
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM memories 
                WHERE LOWER(subject) LIKE ? OR LOWER(predicate) LIKE ? OR LOWER(object_value) LIKE ?
            """, (kw, kw, kw))
            conn.commit()
            count = cursor.rowcount
            logger.info(f"Purged {count} semantic memory facts matching '{keyword}'")
            return count

    def delete_fact_by_id(self, fact_id: int) -> bool:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id=?", (fact_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _increment_evidence(self, fact_id: int) -> None:
        with self.ltm._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE memories 
                SET evidence_count = evidence_count + 1, updated_at = ?
                WHERE id = ?
            """, (time.time(), fact_id))
            conn.commit()

_semantic_memory = SemanticMemory()

def get_semantic_memory() -> SemanticMemory:
    return _semantic_memory
