"""
Unit tests for ActionVerifier (audit #10 / ROADMAP L10 — real verification).

Uses a fake platform adapter so no real OS process is touched. Confirms:
  * open_application that actually launches -> verified True
  * open_application that fails to launch -> verified False (no false positive)
  * close_application when process is gone -> verified True
  * close_application when process lingers -> verified False
  * failed tool result -> verified False immediately
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from raphael.brain import action_verifier
from raphael.brain.action_verifier import ActionVerifier


class FakePlatform:
    """Controllable stand-in for the real platform adapter."""
    def __init__(self, running: set):
        self._running = set(r.lower() for r in running)

    def is_process_running(self, name: str) -> bool:
        return name.lower() in self._running

    def get_foreground_window(self):
        return {"title": None, "app_name": None}

    # unused abstract methods (not exercised here)
    def open_application(self, *a, **k): return {}
    def close_application(self, *a, **k): return {}
    def get_system_metrics(self, *a, **k): return {}
    def set_volume(self, *a, **k): return {}
    def get_volume(self, *a, **k): return {}
    def take_screenshot(self, *a, **k): return {}
    def get_clipboard_text(self, *a, **k): return {}
    def set_clipboard_text(self, *a, **k): return {}
    def launch_browser(self, *a, **k): return {}


def _patch(running):
    fake = FakePlatform(running)
    action_verifier.get_platform_adapter = lambda: fake
    # The ActionVerifier singleton captured a real platform at import time;
    # override its instance attribute so verification uses our fake.
    action_verifier.get_action_verifier().platform = fake
    return fake


def test_open_verified_when_process_runs():
    _patch({"chrome"})
    v = ActionVerifier(poll_attempts=5, poll_interval_s=0.01)
    res = {"status": "success", "action": "open_application"}
    out = asyncio.run(v.verify_action("open_application", {"app_name": "chrome"}, res))
    assert out["verified"] is True, out
    assert "running" in out["reason"]


def test_open_unverified_when_process_absent():
    _patch(set())  # chrome never started
    v = ActionVerifier(poll_attempts=5, poll_interval_s=0.01)
    res = {"status": "success", "action": "open_application"}
    out = asyncio.run(v.verify_action("open_application", {"app_name": "chrome"}, res))
    # This is the key audit fix: status=success but process NOT confirmed.
    assert out["verified"] is False, out
    assert "did not start" in out["reason"]


def test_close_verified_when_gone():
    _patch(set())  # chrome already gone
    v = ActionVerifier(poll_attempts=5, poll_interval_s=0.01)
    res = {"status": "success", "action": "close_application"}
    out = asyncio.run(v.verify_action("close_application", {"app_name": "chrome"}, res))
    assert out["verified"] is True, out
    assert "no longer running" in out["reason"]


def test_close_unverified_when_still_running():
    _patch({"chrome"})  # chrome refused to die
    v = ActionVerifier(poll_attempts=5, poll_interval_s=0.01)
    res = {"status": "success", "action": "close_application"}
    out = asyncio.run(v.verify_action("close_application", {"app_name": "chrome"}, res))
    assert out["verified"] is False, out
    assert "still running" in out["reason"]


def test_failed_tool_not_verified():
    _patch(set())
    v = ActionVerifier()
    res = {"status": "failed", "action": "open_application"}
    out = asyncio.run(v.verify_action("open_application", {"app_name": "chrome"}, res))
    assert out["verified"] is False
    assert "did not report success" in out["reason"]


def test_tool_result_status_downgraded_on_unverify():
    """Integration: execute_tool should mark status 'unverified' on failure."""
    _patch(set())  # chrome won't be confirmed
    from raphael.tools.registry import get_tool_registry
    from raphael.security.permissions import RiskLevel

    reg = get_tool_registry()
    # Inject a tiny tool that reports success but launches nothing.
    called = {}

    @reg.register(name="fake_open", description="test", risk_level=RiskLevel.LOW_RISK)
    def fake_open(app_name: str = ""):
        return {"action": "open_application", "status": "success", "result": {"app_name": app_name}}

    out = asyncio.run(reg.execute_tool("fake_open", {"app_name": "chrome"}))
    assert out.get("status") == "unverified", out
    assert "verification" in out
    assert out["verification"]["verified"] is False
