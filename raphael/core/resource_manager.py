"""
Resource Manager for Raphael AI Assistant.
Monitors CPU, RAM, Disk, and hardware limits to optimize operation mode.
"""

import psutil
import shutil
import time
from typing import Dict, Any
from raphael.core.logging import get_logger
from raphael.core.configuration import get_config

logger = get_logger("resource_manager")

class ResourceMode(str):
    ULTRA_LOW = "ULTRA_LOW"
    LOW = "LOW"
    BALANCED = "BALANCED"
    PERFORMANCE = "PERFORMANCE"

class ResourceManager:
    def __init__(self):
        self.config = get_config()

    def get_system_metrics(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/")

        return {
            "cpu_percent": cpu_percent,
            "ram_total_mb": round(memory.total / (1024 * 1024), 2),
            "ram_used_mb": round(memory.used / (1024 * 1024), 2),
            "ram_available_mb": round(memory.available / (1024 * 1024), 2),
            "ram_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": round((disk.used / disk.total) * 100, 1),
            "timestamp": time.time()
        }

    def recommend_mode(self) -> str:
        metrics = self.get_system_metrics()
        total_ram_gb = metrics["ram_total_mb"] / 1024.0

        if total_ram_gb < 4.0:
            return ResourceMode.ULTRA_LOW
        elif total_ram_gb < 8.0:
            return ResourceMode.LOW
        elif total_ram_gb < 16.0:
            return ResourceMode.BALANCED
        else:
            return ResourceMode.PERFORMANCE

    def get_effective_mode(self) -> str:
        configured = self.config.app.mode
        if configured in [ResourceMode.ULTRA_LOW, ResourceMode.LOW, ResourceMode.BALANCED, ResourceMode.PERFORMANCE]:
            return configured
        return self.recommend_mode()

_resource_manager = ResourceManager()

def get_resource_manager() -> ResourceManager:
    return _resource_manager
