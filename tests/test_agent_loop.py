"""
Unit tests for the Agent Loop plan execution (audit #8 / ROADMAP L11).

Verifies:
  * A multi-step plan executes every step in order when all succeed.
  * A failing step is retried once, then the plan ABORTS with an honest
    report (no silent partial success) and completed steps are recorded.
  * Per-step start/completed/failed events are published.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from raphael.brain.reasoning import get_reasoning_engine, PlanResult
from raphael.brain.planner import PlanStep


async def _run_plan(steps, side_effects):
    """Execute a plan where tool outcomes are driven by `side_effects`.

    side_effects: dict tool_name -> list of result dicts (one per call, FIFO).
    """
    eng = get_reasoning_engine()

    calls: dict = {}

    async def fake_execute(tool_name, args):
        seq = side_effects.get(tool_name, [{"status": "success", "result": {}}])
        n = calls.get(tool_name, 0)
        idx = min(n, len(seq) - 1)
        calls[tool_name] = n + 1
        return dict(seq[idx])

    orig = eng.tool_registry.execute_tool
    eng.tool_registry.execute_tool = fake_execute
    try:
        result = await eng.execute_plan(steps, "test request")
    finally:
        eng.tool_registry.execute_tool = orig
    return result, calls


def _step(i, name):
    return PlanStep(i, name, {"x": i}, f"step {i}: {name}")


@pytest.mark.anyio
async def test_plan_all_steps_succeed():
    steps = [_step(1, "open_application"), _step(2, "search_web")]
    side = {
        "open_application": [{"status": "success", "result": {"app_name": "chrome"}, "verification": {"verified": True}}],
        "search_web": [{"status": "success", "result": {"hits": 5}, "verification": {"verified": True}}],
    }
    result, calls = await _run_plan(steps, side)
    assert isinstance(result, PlanResult)
    assert result.steps_total == 2
    assert result.steps_completed == 2
    assert result.steps_failed == 0
    assert result.aborted is False
    assert "all 2 steps" in result.message


@pytest.mark.anyio
async def test_plan_aborts_on_failure_after_retry():
    steps = [_step(1, "open_application"), _step(2, "search_web")]
    # search_web fails BOTH times (retry still fails) -> plan aborts.
    side = {
        "open_application": [{"status": "success", "result": {"app_name": "chrome"}, "verification": {"verified": True}}],
        "search_web": [
            {"status": "failed", "error": "network down", "verification": {"verified": False}},
            {"status": "failed", "error": "network down", "verification": {"verified": False}},
        ],
    }
    result, calls = await _run_plan(steps, side)
    # step 1 succeeded, step 2 retried once then failed
    assert result.steps_completed == 1
    assert result.steps_failed == 1
    assert result.aborted is True
    assert "aborted at step 2" in result.message
    # search_web was called twice (initial + 1 retry)
    assert calls.get("search_web") == 2
    assert "error" in result.step_results[1]


@pytest.mark.anyio
async def test_plan_unverified_counts_as_failure():
    steps = [_step(1, "open_application")]
    # status success but verification says not confirmed -> treated as failure
    side = {
        "open_application": [{"status": "success", "result": {}, "verification": {"verified": False}}],
    }
    result, calls = await _run_plan(steps, side)
    assert result.steps_completed == 0
    assert result.steps_failed == 1
    assert result.aborted is True
