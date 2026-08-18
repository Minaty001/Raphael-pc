"""
Abstract Platform Adapter interface for Raphael AI Assistant.
Encapsulates OS-specific capabilities (Windows & Linux).
"""

from abc import ABC, abstractmethod
import time
from typing import Dict, Any, Optional

def make_action_result(
    action: str,
    status: str,  # "success", "failed", "denied", "confirmation_required"
    duration_ms: float,
    result: Optional[Any] = None,
    error: Optional[str] = None,
    retryable: bool = False
) -> Dict[str, Any]:
    return {
        "action": action,
        "status": status,
        "result": result,
        "error": error,
        "retryable": retryable,
        "timestamp": time.time(),
        "duration_ms": round(duration_ms, 2)
    }

class PlatformAdapter(ABC):
    @property
    @abstractmethod
    def os_name(self) -> str:
        pass

    @abstractmethod
    def open_application(self, app_name: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def close_application(self, app_name: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_system_metrics(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def set_volume(self, level: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_volume(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def take_screenshot(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_clipboard_text(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def set_clipboard_text(self, text: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def launch_browser(self, url: str) -> Dict[str, Any]:
        pass
