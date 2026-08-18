import pytest
from raphael.memory.vector_store import get_vector_store
from raphael.brain.action_verifier import get_action_verifier
from raphael.proactive.topic_generator import get_topic_generator
from raphael.proactive.morning_continuity import get_morning_continuity

def test_vector_store_search():
    vs = get_vector_store()
    results = vs.search_similar_memories("test preference")
    assert isinstance(results, list)

@pytest.mark.anyio
async def test_action_verification():
    verifier = get_action_verifier()
    res = await verifier.verify_action("system_info", {}, {"status": "success"})
    assert res["verified"] is True

def test_topic_generator():
    tg = get_topic_generator()
    topics = tg.generate_candidate_topics()
    assert isinstance(topics, list)

def test_morning_continuity():
    mc = get_morning_continuity()
    briefing = mc.generate_morning_briefing()
    assert "briefing_text" in briefing
    assert isinstance(briefing["briefing_text"], str)
