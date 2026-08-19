"""
Vector Memory Indexing & Search Engine for Raphael v3 (audit #12 / ROADMAP L5).

Replaces the old bag-of-words term-frequency cosine with a genuine dense
embedding (see ``raphael/memory/embeddings.py``). Memories are embedded once
and scored by SEMANTIC similarity, then re-ranked with metadata
(confidence, recency, importance) so the most relevant, trustworthy, and
recent memories surface first.
"""

import math
import time
from typing import Dict, Any, List, Tuple

from raphael.memory.long_term import get_long_term_memory
from raphael.memory.embeddings import get_embedding_provider, cosine_similarity
from raphael.core.logging import get_logger

logger = get_logger("memory.vector_store")


class VectorStore:
    def __init__(self):
        self.ltm = get_long_term_memory()
        self._embedder = get_embedding_provider()
        self._cache: Dict[int, List[float]] = {}

    def _embedding_for(self, mid: int, text: str) -> List[float]:
        if mid in self._cache:
            return self._cache[mid]
        vec = self._embedder.embed(text)
        self._cache[mid] = vec
        return vec

    def _memory_text(self, m: Dict[str, Any]) -> str:
        return f"{m.get('subject', '')} {m.get('predicate', '')} {m.get('object_value', '')}".strip()

    def search_similar_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Dense-embedding semantic search with metadata re-ranking."""
        memories = self.ltm.list_memories(limit=200)
        if not memories:
            return []

        q_tokens = query.strip().lower()
        if not q_tokens:
            return memories[:top_k]

        q_vec = self._embedder.embed(query)
        now = time.time()
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for m in memories:
            text = self._memory_text(m)
            if not text:
                continue
            m_vec = self._embedding_for(m.get("id", id(m)), text)
            sim = cosine_similarity(q_vec, m_vec)  # semantic similarity in [-1, 1]

            # Metadata re-ranking (audit #13): semantic similarity is the
            # primary signal, modulated by confidence, importance, and recency.
            conf = float(m.get("confidence", 1.0))
            importance = float(m.get("importance", 0.5))
            ts = float(m.get("timestamp", now))
            # Recency: 1.0 if brand new, decaying over ~30 days.
            age_days = max(0.0, (now - ts) / 86400.0)
            recency = math.exp(-age_days / 30.0)

            score = (
                0.60 * max(0.0, sim)
                + 0.15 * conf
                + 0.15 * importance
                + 0.10 * recency
            )
            if sim > 0.0:
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]


_vector_store = VectorStore()


def get_vector_store() -> VectorStore:
    return _vector_store
