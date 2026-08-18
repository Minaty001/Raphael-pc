"""
Resource Manager for Raphael v3 Always-Alive Runtime (FIX 8).

Implements the spec's ResourceManager API (Section 47/48):
    get_cpu_usage()
    get_memory_usage()
    get_available_memory()
    get_gpu_status()
    can_run(task)
    throttle(task)
    pause_background_tasks()
    resume_background_tasks()

Plus configurable resource policy thresholds (Section 48) and battery
detection so laptops can reduce background work on low battery.
"""

import psutil
import shutil
import time
from typing import Dict, Any, Optional

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
        # Cache CPU so the first reading (psutil returns 0 with interval=None)
        # is meaningful. psutil.cpu_percent must be called with a small interval
        # once to "prime" the measurement.
        self._cpu_cache: float = 0.0
        self._cpu_cache_at: float = 0.0
        self._cpu_primed = False
        self._background_paused = False
        # Prime once (non-blocking best-effort).
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    # --- core metrics -----------------------------------------------------
    def get_system_metrics(self) -> Dict[str, Any]:
        cpu = self.get_cpu_usage()
        memory = psutil.virtual_memory()
        disk = shutil.disk_usage("/")
        return {
            "cpu_percent": cpu,
            "ram_total_mb": round(memory.total / (1024 * 1024), 2),
            "ram_used_mb": round(memory.used / (1024 * 1024), 2),
            "ram_available_mb": round(memory.available / (1024 * 1024), 2),
            "ram_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": round((disk.used / disk.total) * 100, 1),
            "battery": self.get_battery(),
            "timestamp": time.time(),
        }

    # --- spec API (Section 47) -------------------------------------------
    def get_cpu_usage(self) -> float:
        """Return a stable, non-zero-on-first-call CPU percentage."""
        now = time.time()
        # Refresh the cached value at most every 1s to avoid jitter.
        if now - self._cpu_cache_at > 1.0:
            try:
                self._cpu_cache = psutil.cpu_percent(interval=None)
            except Exception:
                self._cpu_cache = 0.0
            self._cpu_cache_at = now
            self._cpu_primed = True
        return self._cpu_cache

    def get_memory_usage(self) -> float:
        return psutil.virtual_memory().percent

    def get_available_memory(self) -> float:
        """Available RAM in MB."""
        return round(psutil.virtual_memory().available / (1024 * 1024), 2)

    def get_gpu_status(self) -> Dict[str, Any]:
        """Best-effort GPU probe. Returns unknown if no NVIDIA/ROCm tooling."""
        try:
            import subprocess
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2,
            )
            if out.returncode == 0 and out.stdout.strip():
                used, total, util = [x.strip() for x in out.stdout.split(",")]
                return {"available": True, "used_mb": float(used),
                        "total_mb": float(total), "utilization": float(util)}
        except Exception:
            pass
        return {"available": False, "used_mb": 0, "total_mb": 0, "utilization": 0.0}

    def get_battery(self) -> Dict[str, Any]:
        """Battery state; {} if no battery (desktop)."""
        try:
            bat = psutil.sensors_battery()
            if bat is None:
                return {"available": False}
            return {
                "available": True,
                "percent": bat.percent,
                "plugged_in": bat.power_plugged,
                "low": (not bat.power_plugged) and bat.percent < 20,
            }
        except Exception:
            return {"available": False}

    # --- policy (Section 48) ---------------------------------------------
    def recommend_mode(self) -> str:
        total_ram_gb = self._ram_gb()
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
        if configured in [ResourceMode.ULTRA_LOW, ResourceMode.LOW,
                          ResourceMode.BALANCED, ResourceMode.PERFORMANCE]:
            return configured
        return self.recommend_mode()

    def _ram_gb(self) -> float:
        return psutil.virtual_memory().total / (1024**3)

    # --- task gating (Section 27/28/48) ----------------------------------
    def should_throttle(self, priority: str) -> bool:
        """Decide whether a task of `priority` should be throttled right now."""
        # Foreground/critical never throttled (Section 27/76).
        if priority in ("CRITICAL", "HIGH"):
            return False
        if self._background_paused and priority in ("BACKGROUND", "IDLE", "LOW"):
            return True
        ram_pct = self.get_memory_usage()
        cpu_pct = self.get_cpu_usage()
        cfg = self.config.background
        # Section 48 policy (configurable thresholds).
        if ram_pct > cfg.ram_pause_noncritical_pct or cpu_pct > cfg.cpu_throttle_pct:
            return True
        if ram_pct > cfg.ram_reduce_workers_pct and priority == "IDLE":
            return True
        # Low battery -> reduce background processing.
        bat = self.get_battery()
        if bat.get("available") and bat.get("low") and priority in ("BACKGROUND", "IDLE"):
            return True
        return False

    def can_run(self, task: Any) -> bool:
        """Spec gate: can this task run given current resources?"""
        # Object with .priority attribute or a plain priority string.
        priority = getattr(task, "priority", task) if not isinstance(task, str) else task
        if priority in ("CRITICAL", "HIGH"):
            return True
        # Check hard resource ceilings.
        if self.get_memory_usage() > 95 or self.get_cpu_usage() > 95:
            return False
        if self._background_paused and priority in ("BACKGROUND", "IDLE", "LOW"):
            return False
        return not self.should_throttle(priority)

    def throttle(self, task: Any) -> None:
        """Spec: throttle a running task (best-effort; lowers its urgency)."""
        # For cooperative coroutine tasks we model throttling via a flag the
        # scheduler reads. Heavy CPU work should use a worker/process pool (44).
        try:
            task._throttled = True
        except Exception:
            pass

    def pause_background_tasks(self) -> None:
        self._background_paused = True
        logger.info("ResourceManager: background tasks PAUSED")

    def resume_background_tasks(self) -> None:
        self._background_paused = False
        logger.info("ResourceManager: background tasks RESUMED")

    def is_background_paused(self) -> bool:
        return self._background_paused


_resource_manager = ResourceManager()


def get_resource_manager() -> ResourceManager:
    return _resource_manager
