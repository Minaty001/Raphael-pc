"""
Vector Memory Indexing & Search Engine for Raphael v3.
Provides lightweight vector embeddings, indexing, and hybrid similarity search.
Uses SQLite as the underlying source of truth and vector array calculation.
"""

import math
import re
from typing import List, Dict, Any, Tuple
from raphael.memory.long_term import get_long_term_memory
from raphael.core.logging import get_logger

logger = get_logger("memory.vector_store")

def _simple_tokenize(text: str) -> List[str]:
    return re.findall(r'\w+', text.lower())

def _text_to_vector(text: str, vocab: List[str]) -> List[float]:
    tokens = _simple_tokenize(text)
    token_counts = {}
    for t in tokens:
        token_counts[t] = token_counts.get(t, 0) + 1
    
    vec = []
    for word in vocab:
        vec.append(float(token_counts.get(word, 0)))
    return vec

def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

class VectorStore:
    def __init__(self):
        self.ltm = get_long_term_memory()

    def search_similar_memories(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs hybrid vector similarity search over semantic memories.
        """
        memories = self.ltm.list_memories(limit=200)
        if not memories:
            return []

        query_tokens = _simple_tokenize(query)
        if not query_tokens:
            return memories[:top_k]

        # Build vocabulary
        vocab = list(set(query_tokens))
        for m in memories:
            text = f"{m.get('subject', '')} {m.get('predicate', '')} {m.get('object_value', '')}"
            vocab.extend(_simple_tokenize(text))
        vocab = list(set(vocab))

        query_vec = _text_to_vector(query, vocab)
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for m in memories:
            text = f"{m.get('subject', '')} {m.get('predicate', '')} {m.get('object_value', '')}"
            mem_vec = _text_to_vector(text, vocab)
            sim = _cosine_similarity(query_vec, mem_vec)
            # Factor in memory confidence & evidence count
            conf = float(m.get("confidence", 1.0))
            score = sim * 0.7 + conf * 0.3
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k] if item[0] > 0.1]

_vector_store = VectorStore()

def get_vector_store() -> VectorStore:
    return _vector_store
