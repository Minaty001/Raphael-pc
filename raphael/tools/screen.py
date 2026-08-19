"""
Screen-reading tools for Raphael AI Assistant.

Exposes real on-screen content understanding to the agent loop via the tool
registry: ``read_screen`` captures a screenshot and returns the OCR'd text +
structural context, so "what's on my screen?" becomes answerable.
"""

from typing import Dict, Any, Optional

from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.perception.screen_understanding import get_screen_observer
from raphael.core.logging import get_logger

logger = get_logger("tools.screen")
registry = get_tool_registry()


@registry.register(
    name="read_screen",
    description="Capture the screen and extract visible text/content (OCR + active window context)",
    risk_level=RiskLevel.READ_ONLY,
)
def read_screen(detail: str = "visual") -> Dict[str, Any]:
    """
    detail:
      * "visual"  -> screenshot + OCR text + structured summary (default)
      * "structural" -> active app/window/activity only (cheap, no screenshot)
    """
    observer = get_screen_observer()
    if detail == "structural":
        state = observer.get_structural_state()
        return {
            "status": "success",
            "action": "read_screen",
            "result": {
                "mode": "structural",
                "active_app": state.get("active_app"),
                "window_title": state.get("window_title"),
                "detected_activity": state.get("detected_activity"),
                "visible_error": state.get("visible_error"),
            },
        }

    visual = observer.get_visual_state()
    ocr = visual.get("ocr", {})
    return {
        "status": "success",
        "action": "read_screen",
        "result": {
            "mode": "visual",
            "visual_summary": visual.get("visual_summary", ""),
            "ocr_engine_available": ocr.get("engine_available", False),
            "ocr_text": ocr.get("text", ""),
            "ocr_word_count": ocr.get("word_count", 0),
            "screenshot": (visual.get("screenshot_result", {}) or {})
            .get("result", {})
            .get("file_path"),
            "active_app": visual.get("structural", {}).get("active_app"),
            "window_title": visual.get("structural", {}).get("window_title"),
        },
    }
