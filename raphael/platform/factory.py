"""
Platform Adapter Factory for Raphael AI Assistant.
Detects current Operating System and returns appropriate platform adapter.
"""

import sys
from raphael.platform.common import PlatformAdapter
from raphael.platform.linux import LinuxPlatformAdapter
from raphael.platform.windows import WindowsPlatformAdapter
from raphael.core.logging import get_logger

logger = get_logger("platform.factory")

_platform_adapter_instance = None

def get_platform_adapter() -> PlatformAdapter:
    global _platform_adapter_instance
    if _platform_adapter_instance is None:
        if sys.platform.startswith("win"):
            logger.info("Initializing Windows platform adapter")
            _platform_adapter_instance = WindowsPlatformAdapter()
        else:
            logger.info("Initializing Linux platform adapter")
            _platform_adapter_instance = LinuxPlatformAdapter()
    return _platform_adapter_instance
