"""
Developer Tools for Raphael AI Assistant.
Executes controlled shell commands.
"""

import time
import subprocess
from typing import Dict, Any, Optional
from raphael.tools.registry import get_tool_registry
from raphael.security.permissions import RiskLevel
from raphael.platform.common import make_action_result

registry = get_tool_registry()

@registry.register(name="run_command", description="Execute shell command", risk_level=RiskLevel.HIGH_RISK)
def run_command(command: str, cwd: Optional[str] = None, timeout_seconds: int = 10) -> Dict[str, Any]:
    start_time = time.time()
    try:
        res = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        duration = (time.time() - start_time) * 1000
        status = "success" if res.returncode == 0 else "failed"
        return make_action_result(
            "run_command",
            status,
            duration,
            result={
                "command": command,
                "returncode": res.returncode,
                "stdout": res.stdout[:2000],
                "stderr": res.stderr[:2000]
            },
            error=res.stderr.strip() if res.returncode != 0 else None
        )
    except subprocess.TimeoutExpired:
        duration = (time.time() - start_time) * 1000
        return make_action_result("run_command", "failed", duration, error=f"Command execution timed out after {timeout_seconds} seconds")
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        return make_action_result("run_command", "failed", duration, error=str(e))
