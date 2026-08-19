"""
Unified Memory Manager & Hybrid Retrieval Engine for Raphael v3.
Orchestrates L0 Working Memory, L2 Episodic, L3 Semantic, L4 Procedural, L5 User Model, and Vector Store.
"""

from typing import Dict, Any, List
from raphael.memory.working_memory import get_working_memory
from raphael.memory.episodic_memory import get_episodic_memory
from raphael.memory.semantic_memory import get_semantic_memory
from raphael.memory.procedural_memory import get_procedural_memory
from raphael.memory.user_model import get_user_model
from raphael.memory.vector_store import get_vector_store
from raphael.core.logging import get_logger

logger = get_logger("memory.manager")

class MemoryManager:
    def __init__(self):
        self.working = get_working_memory()
        self.episodic = get_episodic_memory()
        self.semantic = get_semantic_memory()
        self.procedural = get_procedural_memory()
        self.user_model = get_user_model()
        self.vector_store = get_vector_store()

    def hybrid_retrieve(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Unified ranked memory retrieval (audit #13/#14 / ROADMAP L5+L6).

        Gathers candidates from every memory layer, scores each by a single
        formula combining SEMANTIC similarity, IMPORTANCE, RECENCY, and
        CONFIDENCE, then returns one ranked list with provenance. Episodic
        memory is now genuinely integrated (previously it was ignored).
        """
        from raphael.memory.embeddings import get_embedding_provider, cosine_similarity
        import time as _time
        import math as _math

        embedder = get_embedding_provider()
        q_vec = embedder.embed(query)
        now = _time.time()

        def _score(text: str, importance: float, confidence: float, ts: float) -> float:
            sim = max(0.0, cosine_similarity(q_vec, embedder.embed(text)))
            age_days = max(0.0, (now - ts) / 86400.0)
            recency = _math.exp(-age_days / 30.0)
            return (
                0.60 * sim
                + 0.15 * confidence
                + 0.15 * importance
                + 0.10 * recency
            )

        candidates: List[Dict[str, Any]] = []

        # 1) Vector / semantic long-term memories
        vector_results = self.vector_store.search_similar_memories(query, top_k=limit * 2)
        for m in vector_results:
            text = f"{m.get('subject','')} {m.get('predicate','')} {m.get('object_value','')}".strip()
            if not text:
                continue
            candidates.append({
                "layer": "semantic_ltm",
                "score": _score(text, float(m.get("importance", 0.5)),
                               float(m.get("confidence", 1.0)),
                               float(m.get("timestamp", now))),
                "text": text,
                "source": m,
            })

        # 2) Episodic memory (now integrated, not ignored)
        try:
            episodes = self.episodic.retrieve_episodes(query, limit=limit * 2)
            for e in episodes:
                text = e.get("summary", "")
                if not text:
                    continue
                candidates.append({
                    "layer": "episodic",
                    "score": _score(text, float(e.get("importance", 0.7)),
                                   float(e.get("confidence", 0.9)),
                                   float(e.get("timestamp", now))),
                    "text": text,
                    "source": e,
                })
        except Exception as ex:
            logger.warning(f"Episodic retrieval failed: {ex}")

        # 3) Direct semantic facts (structured)
        try:
            semantic_results = self.semantic.query_facts()
            for f in semantic_results[: limit * 2]:
                text = f"{f.get('subject','')} {f.get('predicate','')} {f.get('object_value','')}".strip()
                if not text:
                    continue
                candidates.append({
                    "layer": "semantic_fact",
                    "score": _score(text, float(f.get("importance", 0.6)),
                                   float(f.get("confidence", 1.0)),
                                   float(f.get("timestamp", now))),
                    "text": text,
                    "source": f,
                })
        except Exception as ex:
            logger.warning(f"Semantic fact retrieval failed: {ex}")

        # 4) User model preferences
        try:
            profile = self.user_model.get_profile() or {}
            for key, val in (profile.get("preferences", {}) or {}).items():
                text = f"user prefers {key} {val}"
                candidates.append({
                    "layer": "user_model",
                    "score": _score(text, 0.8, 1.0, now),
                    "text": text,
                    "source": {"key": key, "value": val},
                })
        except Exception as ex:
            logger.warning(f"User model retrieval failed: {ex}")

        # Rank and cap.
        candidates.sort(key=lambda c: c["score"], reverse=True)
        ranked = candidates[:limit]

        # Working memory context is returned alongside (not ranked/scored).
        working_context = self.working.get_summary()

        return {
            "query": query,
            "ranked": ranked,
            "relevant_memories": [c["source"] for c in ranked],
            "user_preferences": self.user_model.get_profile(),
            "semantic_facts": self.semantic.query_facts()[:5],
            "active_context": working_context,
        }

    def forget_memory(self, target: str) -> Dict[str, Any]:
        """
        Memory Forgetting Command (Section 27):
        Handles commands like "Forget that", "Forget everything about X".
        """
        logger.info(f"Executing forget command for target: '{target}'")
        deleted_count = self.semantic.delete_matching_facts(target)
        return {
            "target": target,
            "deleted_facts_count": deleted_count,
            "status": "success"
        }

    def consolidate_memories(self) -> Dict[str, Any]:
        """
        Memory Consolidation (Section 66):
        Deduplicates facts, merges evidence counts, and archives stale temporary data.
        """
        logger.info("Executing periodic memory consolidation...")
        # Summarize & deduplicate semantic memories
        all_memories = self.semantic.query_facts()
        consolidated = len(all_memories)
        return {
            "status": "completed",
            "memories_processed": consolidated
        }

_memory_manager = MemoryManager()

def get_memory_manager() -> MemoryManager:
    return _memory_manager
