import pytest
from raphael.learning.learning_engine import get_learning_engine
from raphael.learning.reflection_engine import get_reflection_engine

@pytest.mark.anyio
async def test_learning_feedback():
    le = get_learning_engine()
    res = await le.process_feedback("I prefer OpenRouter as my primary provider")
    assert res is not None
    assert res["type"] == "preference"
    assert res["value"] == "openrouter"

@pytest.mark.anyio
async def test_self_reflection():
    re = get_reflection_engine()
    tool_res = {"status": "success", "duration_ms": 45}
    ref = await re.reflect_on_task("system_info", tool_res, "check system info")
    assert ref["status"] == "success"
    assert "lesson" in ref
