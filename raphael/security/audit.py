"""
Audit Logging System for Raphael AI Assistant.
Logs all privileged actions for security and debugging.
"""

import time
from typing import Dict, Any, Optional
from raphael.core.logging import get_logger

logger = get_logger("security.audit")

class AuditLogger:
    def log_action(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        permission_level: str,
        status: str,
        user_request: Optional[str] = None,
        intent: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: float = 0.0
    ) -> Dict[str, Any]:
        record = {
            "timestamp": time.time(),
            "user_request": user_request,
            "intent": intent,
            "tool": tool_name,
            "arguments": arguments,
            "permission_level": permission_level,
            "status": status,
            "result": result,
            "error": error,
            "duration_ms": duration_ms
        }
        logger.info(f"AUDIT | Tool: {tool_name} | Status: {status} | Risk: {permission_level} | Duration: {duration_ms:.1f}ms")
        return record

_audit_logger = AuditLogger()

def get_audit_logger() -> AuditLogger:
    return _audit_logger
