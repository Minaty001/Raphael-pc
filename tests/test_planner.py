"""
Unit tests for the LLM-driven Planner (ROADMAP L8 / audit: planner was just
pattern-matched).

Verifies deterministic patterns still work, LLM decomposition produces valid
ordered steps, unknown tools are dropped, and any LLM failure degrades to an
empty plan. Also covers the robust JSON-array extractor.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from raphael.brain.planner import get_planner, _extract_json_array
from raphael.brain.planner import PlanStep


@pytest.mark.anyio
async def test_pattern_plan_still_works():
    planner = get_planner()
    steps = await planner.create_plan("open chrome and search for weather")
    assert len(steps) == 2
    assert steps[0].tool_name == "open_application"
    assert steps[1].tool_name == "search_web"
    assert steps[1].args.get("query") == "weather"


def test_extract_json_array_robust():
    assert _extract_json_array("[]") == []
    assert _extract_json_array('```json\n[{"tool_name":"open_application"}]\n```') == [
        {"tool_name": "open_application"}
    ]
    assert _extract_json_array("Here is the plan: [{\"a\":1}] done.") == [{"a": 1}]
    assert _extract_json_array("no json here") is None
    assert _extract_json_array("") is None


@pytest.mark.anyio
async def test_llm_plan_produces_valid_steps(monkeypatch):
    planner = get_planner()

    fake_json = (
        '```json\n'
        '[\n'
        '  {"tool_name": "open_application", "args": {"app_name": "terminal"}, "description": "Open terminal"},\n'
        '  {"tool_name": "system_info", "args": {}, "description": "Get system info"}\n'
        ']\n'
        '```'
    )

    class FakeRouter:
        async def chat(self, messages):
            return fake_json

    class FakeRegistry:
        def list_tools(self):
            return [
                {"name": "open_application", "description": "open app", "parameters": ["app_name"]},
                {"name": "system_info", "description": "sys info", "parameters": []},
            ]

    import raphael.brain.llm_router as LR
    import raphael.tools.registry as REG

    monkeypatch.setattr(LR, "get_llm_router", lambda: FakeRouter())
    monkeypatch.setattr(REG, "get_tool_registry", lambda: FakeRegistry())

    # A request that does NOT match a deterministic pattern -> LLM path.
    steps = await planner.create_plan("set up my dev environment and check the system")
    assert len(steps) == 2
    assert steps[0].tool_name == "open_application"
    assert steps[0].args == {"app_name": "terminal"}
    assert steps[1].tool_name == "system_info"
    # Step ordering preserved.
    assert [s.step_id for s in steps] == [1, 2]


@pytest.mark.anyio
async def test_llm_plan_drops_unknown_tools(monkeypatch):
    planner = get_planner()
    fake_json = (
        '[{"tool_name": "open_application", "args": {"app_name": "chrome"}},'
        ' {"tool_name": "magic_unknown_tool", "args": {}}]'
    )

    class FakeRouter:
        async def chat(self, messages):
            return fake_json

    class FakeRegistry:
        def list_tools(self):
            return [
                {"name": "open_application", "description": "open app", "parameters": ["app_name"]},
            ]

    import raphael.brain.llm_router as LR
    import raphael.tools.registry as REG

    monkeypatch.setattr(LR, "get_llm_router", lambda: FakeRouter())
    monkeypatch.setattr(REG, "get_tool_registry", lambda: FakeRegistry())

    steps = await planner.create_plan("do something complicated")
    # Only the known tool survives.
    assert [s.tool_name for s in steps] == ["open_application"]


@pytest.mark.anyio
async def test_llm_failure_degrades_to_empty(monkeypatch):
    planner = get_planner()

    class FakeRouter:
        async def chat(self, messages):
            raise RuntimeError("LLM provider down")

    import raphael.brain.llm_router as LR

    monkeypatch.setattr(LR, "get_llm_router", lambda: FakeRouter())

    steps = await planner.create_plan("prepare my project for testing")
    # Graceful: empty plan -> reasoning engine falls back to chat.
    assert steps == []


def test_planstep_fields():
    s = PlanStep(1, "open_application", {"app_name": "chrome"}, "open chrome")
    assert s.step_id == 1
    assert s.status == "pending"
    assert s.result is None
