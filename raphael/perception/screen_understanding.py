"""
Screen Understanding Module for Raphael AI Assistant.
Combines Structural UI understanding (window titles, processes, UI automation)
and Visual Screen understanding (OCR, visual state summary).
"""

import os
import sys
import time
import subprocess
import shutil
from typing import Dict, Any, Optional, List
from raphael.platform.factory import get_platform_adapter
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.perception.ocr import get_ocr_provider

logger = get_logger("perception.screen")

class ScreenObserver:
    def __init__(self):
        self.config = get_config()
        self.last_screen_state: Optional[Dict[str, Any]] = None

    def get_structural_state(self) -> Dict[str, Any]:
        """
        Retrieves active window title, process name, and structural UI metadata.
        Cheap and accurate.
        """
        adapter = get_platform_adapter()
        state = {
            "timestamp": time.time(),
            "active_app": "Unknown",
            "window_title": "Unknown",
            "detected_activity": "General desktop activity",
            "visible_error": None
        }

        if adapter.os_name == "linux":
            if shutil.which("xdotool"):
                try:
                    res_title = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True, timeout=1.0)
                    if res_title.returncode == 0:
                        state["window_title"] = res_title.stdout.strip()
                    
                    res_pid = subprocess.run(["xdotool", "getactivewindow", "getwindowpid"], capture_output=True, text=True, timeout=1.0)
                    if res_pid.returncode == 0 and res_pid.stdout.strip().isdigit():
                        pid = int(res_pid.stdout.strip())
                        import psutil
                        proc = psutil.Process(pid)
                        state["active_app"] = proc.name()
                except Exception:
                    pass

        elif adapter.os_name == "windows":
            try:
                ps_script = "(Get-Process | Where-Object {$_.MainWindowHandle -ne 0} | Select-Object -First 1 ProcessName, MainWindowTitle) | ConvertTo-Json"
                res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, timeout=2.0)
                if res.returncode == 0 and res.stdout.strip():
                    import json
                    parsed = json.loads(res.stdout)
                    state["active_app"] = parsed.get("ProcessName", "WindowsApp")
                    state["window_title"] = parsed.get("MainWindowTitle", "")
            except Exception:
                pass

        # Activity inference
        title_lower = state["window_title"].lower()
        app_lower = state["active_app"].lower()

        if "code" in app_lower or "vscode" in title_lower or ".py" in title_lower or ".ts" in title_lower:
            state["detected_activity"] = "Coding / Software Development"
            if "error" in title_lower or "exception" in title_lower or "traceback" in title_lower:
                state["visible_error"] = "Build / Runtime Error Detected"
        elif "chrome" in app_lower or "firefox" in app_lower or "browser" in app_lower:
            state["detected_activity"] = "Web Browsing"
            if "youtube" in title_lower:
                state["detected_activity"] = "Watching Video / Media"
            elif "github" in title_lower or "stack overflow" in title_lower:
                state["detected_activity"] = "Developer Research"
        elif "terminal" in app_lower or "bash" in title_lower or "cmd" in app_lower:
            state["detected_activity"] = "Terminal / Shell Operations"

        self.last_screen_state = state
        return state

    def get_visual_state(self) -> Dict[str, Any]:
        """
        Captures a screenshot and extracts real on-screen content (OCR) so
        perception knows WHAT is on screen, not just which app owns the window.
        Degrades gracefully when no OCR engine is installed.
        """
        adapter = get_platform_adapter()
        shot_res = adapter.take_screenshot()
        structural = self.get_structural_state()

        ocr = {"provider": "offline", "engine_available": False, "text": "",
               "word_count": 0, "note": "OCR not run"}
        screenshot_path = shot_res.get("result", {}).get("file_path") if isinstance(shot_res, dict) else None
        if screenshot_path and os.path.isfile(screenshot_path):
            try:
                ocr = get_ocr_provider().extract_text(screenshot_path)
            except Exception as e:  # never let OCR break perception
                logger.warning(f"OCR extraction failed: {e}")
                ocr = {"provider": "offline", "engine_available": False,
                       "text": "", "word_count": 0, "note": f"OCR error: {e}"}

        ocr_text = (ocr.get("text") or "").strip()
        if ocr.get("engine_available") and ocr_text:
            visual_summary = (
                f"User is in '{structural['active_app']}' "
                f"({structural['window_title']}). On-screen text detected "
                f"({ocr.get('word_count', 0)} words): {ocr_text[:280]}"
            )
        else:
            visual_summary = (
                f"User is interacting with '{structural['active_app']}' "
                f"(Window: '{structural['window_title']}'). "
                f"Activity: {structural['detected_activity']}. "
                f"[OCR engine not available: {ocr.get('note', 'n/a')}]"
            )

        return {
            "screenshot_result": shot_res,
            "structural": structural,
            "ocr": ocr,
            "visual_summary": visual_summary,
            "timestamp": time.time()
        }

    def explain_current_screen(self, user_question: str) -> str:
        """
        Screen-aware assistance: answers contextual questions like 'What am I looking at?'
        """
        struct = self.get_structural_state()
        app = struct["active_app"]
        title = struct["window_title"]
        act = struct["detected_activity"]
        err = struct.get("visible_error")

        if "error" in user_question.lower():
            if err:
                return f"You are in {app} ({title}). A build/runtime issue is visible in your active window: '{err}'."
            return f"You are currently working in {app} ({title}). No explicit error string is highlighted in the active window title."

        return f"You are looking at '{app}' with window title '{title}'. Detected Activity: {act}."

_screen_observer = ScreenObserver()

def get_screen_observer() -> ScreenObserver:
    return _screen_observer
