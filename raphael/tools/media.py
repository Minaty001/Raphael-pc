"""
Media Control Tools for Raphael AI Assistant.
"""

from typing import Dict, Any
from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.platform.factory import get_platform_adapter

registry = get_tool_registry()

@registry.register(name="set_volume", description="Set audio playback volume level (0-100)", risk_level=RiskLevel.LOW_RISK)
def set_volume(level: int) -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.set_volume(level)

@registry.register(name="get_volume", description="Get current audio volume level", risk_level=RiskLevel.READ_ONLY)
def get_volume() -> Dict[str, Any]:
    adapter = get_platform_adapter()
    return adapter.get_volume()
