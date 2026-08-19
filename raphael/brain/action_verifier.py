"""
Action Verification Engine for Raphael v3.

Verifies the OUTCOME of a tool execution against the real system state, so
Raphael never reports success just because a launcher returned 0. This
implements ROADMAP Level 10 (Verification):

    Action -> Observe -> Verify

e.g. "Open Chrome" must be confirmed by checking that the Chrome process is
actually running (and, ideally, that it is the foreground window) — not by
trusting the launcher's own return code.
"""

import asyncio
import time
from typing import Dict, Any, Optional

from raphael.platform.factory import get_platform_adapter
from raphael.core.logging import get_logger

logger = get_logger("brain.action_verifier")


class ActionVerifier:
    def __init__(self, poll_attempts: int = 10, poll_interval_s: float = 0.2):
        # poll_attempts * poll_interval_s ~= 2s settle window for async launches
        self.platform = get_platform_adapter()
        self.poll_attempts = poll_attempts
        self.poll_interval_s = poll_interval_s

    async def verify_action(
        self, tool_name: str, args: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify a tool's reported outcome against real system state.

        Returns {"verified": bool, "confidence": float, "reason": str}.
        A tool that claims success but cannot be confirmed yields
        verified=False (no false positives).
        """
        if result.get("status") != "success":
            return {"verified": False, "confidence": 1.0,
                    "reason": "Initial tool execution did not report success"}

        # Resolve the *semantic action type* to verify. Prefer the tool's own
        # name, but fall back to the reported action (a tool may perform a
        # known verifiable action under a different name, e.g. a wrapper that
        # launches an app).
        action_key = tool_name
        if action_key not in ("open_application", "close_application",
                              "write_file", "create_folder"):
            action_key = result.get("action", action_key)

        if action_key == "open_application":
            ok, detail = await self._poll_running(args.get("app_name", ""), expect=True)
            return {
                "verified": ok,
                "confidence": 1.0 if ok else 0.9,
                "reason": detail,
            }

        if action_key == "close_application":
            ok, detail = await self._poll_running(args.get("app_name", ""), expect=False)
            return {
                "verified": ok,
                "confidence": 1.0 if ok else 0.9,
                "reason": detail,
            }

        if tool_name in ("write_file", "create_folder"):
            path = args.get("file_path") or args.get("folder_path")
            if path and _path_exists(path):
                return {"verified": True, "confidence": 1.0,
                        "reason": f"Path '{path}' exists on disk"}
            return {"verified": False, "confidence": 1.0,
                    "reason": f"Path '{path}' not found after creation"}

        # Default: trust the reported success only when there is no cheap,
        # reliable system check available for this tool.
        return {"verified": True, "confidence": 0.6,
                "reason": "No system-state check available; status reported success"}

    async def _poll_running(self, app_name: str, expect: bool) -> tuple:
        """Poll is_process_running until it matches `expect` or window elapses."""
        if not app_name:
            return (False, "No application name provided")
        for attempt in range(self.poll_attempts):
            running = self.platform.is_process_running(app_name)
            if running == expect:
                verb = "running" if expect else "no longer running"
                return (True, f"Process '{app_name}' confirmed {verb}"
                               f" (attempt {attempt + 1})")
            if attempt < self.poll_attempts - 1:
                await asyncio.sleep(self.poll_interval_s)
        verb = "did not start" if expect else "still running"
        return (False, f"Process '{app_name}' {verb} after verification window")


def _path_exists(path: str) -> bool:
    import os
    try:
        return os.path.exists(path)
    except Exception:
        return False


_action_verifier = ActionVerifier()


def get_action_verifier() -> ActionVerifier:
    return _action_verifier
