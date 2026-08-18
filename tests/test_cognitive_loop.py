import pytest
from raphael.brain.cognitive_runtime import get_cognitive_runtime

@pytest.mark.anyio
async def test_cognitive_cycle_execution():
    cog = get_cognitive_runtime()
    
    # Test idle perception cycle
    cycle_res = await cog.execute_cognitive_cycle()
    assert "observation" in cycle_res
    assert "cycle_duration_ms" in cycle_res

    # Test user input processing cognitive cycle
    user_res = await cog.execute_cognitive_cycle("show system info")
    assert "text" in user_res or "response" in user_res
    assert "duration_ms" in user_res
