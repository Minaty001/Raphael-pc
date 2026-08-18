"""
System Tools for Raphael AI Assistant.
"""

from typing import Dict, Any, Optional
from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.platform.factory import get_platform_adapter

registry = get_tool_registry()

@registry.register(name="system_info", description="Get CPU, RAM, and Disk metrics", risk_level=RiskLevel.READ_ONLY)
def system_info() -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.get_system_metrics()

@registry.register(name="take_screenshot", description="Capture screen screenshot", risk_level=RiskLevel.LOW_RISK)
def take_screenshot(output_path: Optional[str] = None) -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.take_screenshot(output_path)

@registry.register(name="clipboard_read", description="Read current clipboard text", risk_level=RiskLevel.READ_ONLY)
def clipboard_read() -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.get_clipboard_text()

@registry.register(name="clipboard_write", description="Write text to clipboard", risk_level=RiskLevel.MODERATE)
def clipboard_write(text: str) -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.set_clipboard_text(text)
