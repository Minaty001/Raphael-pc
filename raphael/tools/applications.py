"""
Application Tools for Raphael AI Assistant.
"""

from typing import Dict, Any
from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.platform.factory import get_platform_adapter

registry = get_tool_registry()

@registry.register(name="open_application", description="Launch desktop application by name", risk_level=RiskLevel.LOW_RISK)
def open_application(app_name: str) -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.open_application(app_name)

@registry.register(name="close_application", description="Close running desktop application by name", risk_level=RiskLevel.MODERATE)
def close_application(app_name: str) -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.close_application(app_name)
