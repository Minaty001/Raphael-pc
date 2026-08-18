import pytest
from raphael.memory.working_memory import get_working_memory
from raphael.memory.episodic_memory import get_episodic_memory
from raphael.memory.semantic_memory import get_semantic_memory, SemanticType
from raphael.memory.procedural_memory import get_procedural_memory
from raphael.memory.user_model import get_user_model
from raphael.memory.memory_manager import get_memory_manager

def test_working_memory():
    wm = get_working_memory()
    wm.set_active_goal("Test Goal")
    wm.add_unresolved_question("How to test?")
    summary = wm.get_summary()

    assert summary["active_goal"] == "Test Goal"
    assert "How to test?" in summary["unresolved_questions"]

def test_semantic_and_user_model():
    sm = get_semantic_memory()
    fact_id = sm.store_fact("user", "prefers_theme", "dark", fact_type=SemanticType.PREFERENCE)
    assert fact_id > 0

    facts = sm.query_facts("user", "prefers_theme")
    assert len(facts) > 0
    assert facts[0]["object_value"] == "dark"

    um = get_user_model()
    um.record_preference("theme", "dark")
    profile = um.get_profile()
    assert "theme" in profile
    assert profile["theme"]["value"] == "dark"

def test_memory_forget():
    sm = get_semantic_memory()
    sm.store_fact("test_entity", "is_temporary", "true")
    mm = get_memory_manager()
    res = mm.forget_memory("test_entity")
    assert res["status"] == "success"
    assert res["deleted_facts_count"] >= 1
