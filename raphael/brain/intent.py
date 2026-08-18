"""
Intent Engine for Raphael AI Assistant.
Rule-based fast classifier for common desktop intents to bypass heavy LLMs.
"""

import re
from typing import Dict, Any, Optional

class IntentType:
    OPEN_APP = "OPEN_APP"
    CLOSE_APP = "CLOSE_APP"
    SEARCH_WEB = "SEARCH_WEB"
    SYSTEM_STATUS = "SYSTEM_STATUS"
    TAKE_SCREENSHOT = "TAKE_SCREENSHOT"
    SET_VOLUME = "SET_VOLUME"
    READ_FILE = "READ_FILE"
    WRITE_FILE = "WRITE_FILE"
    RUN_COMMAND = "RUN_COMMAND"
    GENERAL_CHAT = "GENERAL_CHAT"

class IntentEngine:
    def classify(self, text: str) -> Dict[str, Any]:
        clean = text.strip().lower()

        # Open application pattern
        match = re.search(r"^(?:open|launch|start|run)\s+([a-z0-9_\-\s]+)$", clean)
        if match and not any(kw in clean for kw in ["web", "google", "youtube", "url", "http"]):
            app = match.group(1).strip()
            if app not in ["file", "folder", "command", "terminal"]:
                return {
                    "matched": True,
                    "intent": IntentType.OPEN_APP,
                    "tool": "open_application",
                    "tool_name": "open_application",
                    "args": {"app_name": app},
                    "tool_args": {"app_name": app},
                    "confidence": 0.95
                }

        # Close application pattern
        match = re.search(r"^(?:close|kill|stop|terminate)\s+([a-z0-9_\-\s]+)$", clean)
        if match:
            app = match.group(1).strip()
            return {
                "matched": True,
                "intent": IntentType.CLOSE_APP,
                "tool": "close_application",
                "tool_name": "close_application",
                "args": {"app_name": app},
                "tool_args": {"app_name": app},
                "confidence": 0.95
            }

        # System status
        if any(phrase in clean for phrase in ["system info", "cpu usage", "ram usage", "system status", "system metrics", "how is system"]):
            return {
                "matched": True,
                "intent": IntentType.SYSTEM_STATUS,
                "tool": "system_info",
                "tool_name": "system_info",
                "args": {},
                "tool_args": {},
                "confidence": 0.95
            }

        # Screenshot
        if "screenshot" in clean or "capture screen" in clean or "take screen" in clean:
            return {
                "matched": True,
                "intent": IntentType.TAKE_SCREENSHOT,
                "tool": "take_screenshot",
                "tool_name": "take_screenshot",
                "args": {},
                "tool_args": {},
                "confidence": 0.95
            }

        # Volume control
        match = re.search(r"set volume (?:to\s+)?(\d+)%?", clean)
        if match:
            vol = int(match.group(1))
            return {
                "matched": True,
                "intent": IntentType.SET_VOLUME,
                "tool": "set_volume",
                "tool_name": "set_volume",
                "args": {"level": vol},
                "tool_args": {"level": vol},
                "confidence": 0.95
            }

        # Web search
        match = re.search(r"^(?:search|google|find on web|look up)\s+(?:for\s+)?(.+)$", clean)
        if match:
            query = match.group(1).strip()
            return {
                "matched": True,
                "intent": IntentType.SEARCH_WEB,
                "tool": "search_web",
                "tool_name": "search_web",
                "args": {"query": query},
                "tool_args": {"query": query},
                "confidence": 0.90
            }

        # General LLM conversation fallback
        return {
            "matched": False,
            "intent": IntentType.GENERAL_CHAT,
            "tool": None,
            "tool_name": None,
            "args": {},
            "tool_args": {},
            "confidence": 0.50
        }

    def classify_intent(self, text: str) -> Dict[str, Any]:
        return self.classify(text)

_intent_engine = IntentEngine()

def get_intent_engine() -> IntentEngine:
    return _intent_engine
