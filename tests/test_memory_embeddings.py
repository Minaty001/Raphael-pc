"""
Unit tests for the embedding-based memory (audit #12/#13/#14 / ROADMAP L5+L6).

No external model required: uses the deterministic LocalHashingEmbedding.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from raphael.memory.embeddings import LocalHashingEmbedding, cosine_similarity


def test_embedding_is_deterministic():
    e = LocalHashingEmbedding(dim=128)
    a = e.embed("Raphael fixed the login bug yesterday")
    b = e.embed("Raphael fixed the login bug yesterday")
    assert a == b, "identical inputs must produce identical embeddings"
    assert len(a) == 128


def test_embedding_similarity_orders_correctly():
    e = LocalHashingEmbedding(dim=128)
    base = e.embed("fix the login authentication bug")
    similar = e.embed("resolve login auth failure")
    unrelated = e.embed("play some relaxing music on spotify")
    s_sim = cosine_similarity(base, similar)
    s_unrel = cosine_similarity(base, unrelated)
    assert s_sim > s_unrel, f"similar ({s_sim}) should outrank unrelated ({s_unrel})"
    assert s_sim > 0.0


def test_cosine_orthogonal_zero():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_vector_store_ranks_by_semantics():
    from raphael.memory import vector_store as vs_mod

    # Fake LTM returning two memories: one about login, one about music.
    class FakeLTM:
        def list_memories(self, limit=200):
            return [
                {"id": 1, "subject": "login", "predicate": "had", "object_value": "a bug",
                 "confidence": 1.0, "importance": 0.8, "timestamp": time.time()},
                {"id": 2, "subject": "music", "predicate": "play", "object_value": "spotify",
                 "confidence": 1.0, "importance": 0.8, "timestamp": time.time()},
            ]

    store = vs_mod.VectorStore()
    store.ltm = FakeLTM()
    store._embedder = LocalHashingEmbedding()
    store._cache = {}

    results = store.search_similar_memories("fix the login authentication bug", top_k=2)
    assert results, "expected at least one result"
    assert results[0]["id"] == 1, f"login memory should rank first, got {results[0].get('id')}"


def test_hybrid_retrieve_integrates_episodic():
    from raphael.memory import memory_manager as mm_mod
    from raphael.memory.embeddings import LocalHashingEmbedding

    # Minimal fakes for each memory layer.
    class FakeEpisodic:
        def retrieve_episodes(self, query, limit=10):
            return [{"id": 99, "summary": "fixed the login bug on the auth service",
                     "importance": 0.9, "confidence": 0.9, "timestamp": time.time()}]

    class FakeSemantic:
        def query_facts(self, subject=None, predicate=None):
            return []

    class FakeUser:
        def get_profile(self):
            return {"preferences": {}}

    class FakeWorking:
        def get_summary(self):
            return "working context"

    class FakeVec:
        def search_similar_memories(self, query, top_k=5):
            return []

    mgr = mm_mod.MemoryManager.__new__(mm_mod.MemoryManager)
    mgr.episodic = FakeEpisodic()
    mgr.semantic = FakeSemantic()
    mgr.user_model = FakeUser()
    mgr.working = FakeWorking()
    mgr.vector_store = FakeVec()

    out = mgr.hybrid_retrieve("what did we do about the login bug yesterday", limit=5)
    ranked = out.get("ranked", [])
    assert ranked, "expected ranked results"
    # The episodic memory about the login bug must be present and ranked.
    summaries = [c["text"] for c in ranked]
    assert any("login bug" in s for s in summaries), f"episodic login memory missing: {summaries}"
    # Every ranked item carries provenance + a numeric score.
    for c in ranked:
        assert "layer" in c and "score" in c and isinstance(c["score"], float)
