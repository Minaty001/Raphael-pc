import pytest
import raphael.tools.system
import raphael.tools.applications
from raphael.tools.registry import get_tool_registry

@pytest.mark.anyio
async def test_tool_registry_execution():
    registry = get_tool_registry()
    tool = registry.get_tool("system_info")
    assert tool is not None

    res = await tool.execute()
    assert res["status"] == "success"
    assert "result" in res
    assert "duration_ms" in res
    assert "timestamp" in res
