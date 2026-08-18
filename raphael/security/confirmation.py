"""
Confirmation Manager for Raphael AI Assistant.
Handles pending confirmation requests for privileged operations.
"""

import asyncio
import uuid
import time
from typing import Dict, Any, Optional
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus

logger = get_logger("security.confirmation")

class PendingConfirmation:
    def __init__(self, request_id: str, tool_name: str, args: Dict[str, Any], reason: str, timeout_seconds: int = 30):
        self.request_id = request_id
        self.tool_name = tool_name
        self.args = args
        self.reason = reason
        self.created_at = time.time()
        self.timeout_at = self.created_at + timeout_seconds
        self.future: asyncio.Future = asyncio.Future()

class ConfirmationManager:
    def __init__(self):
        self._pending: Dict[str, PendingConfirmation] = {}

    async def request_confirmation(self, tool_name: str, args: Dict[str, Any], reason: str, timeout_seconds: int = 30) -> bool:
        request_id = str(uuid.uuid4())[:8]
        pending = PendingConfirmation(request_id, tool_name, args, reason, timeout_seconds)
        self._pending[request_id] = pending

        logger.info(f"Confirmation requested [ID: {request_id}] for tool '{tool_name}': {reason}")

        await get_event_bus().publish(
            "security.confirm_request",
            {
                "request_id": request_id,
                "tool_name": tool_name,
                "args": args,
                "reason": reason,
                "timeout_seconds": timeout_seconds
            },
            source="confirmation_manager"
        )

        try:
            approved = await asyncio.wait_for(pending.future, timeout=timeout_seconds)
            logger.info(f"Confirmation [ID: {request_id}] result: {'APPROVED' if approved else 'DENIED'}")
            return approved
        except asyncio.TimeoutError:
            logger.warning(f"Confirmation [ID: {request_id}] timed out after {timeout_seconds}s")
            return False
        finally:
            self._pending.pop(request_id, None)

    def resolve_confirmation(self, request_id: str, approved: bool) -> bool:
        if request_id in self._pending:
            pending = self._pending[request_id]
            if not pending.future.done():
                pending.future.set_result(approved)
                return True
        return False

    def list_pending(self) -> Dict[str, Any]:
        return {
            req_id: {
                "request_id": p.request_id,
                "tool_name": p.tool_name,
                "args": p.args,
                "reason": p.reason,
                "time_remaining": max(0, p.timeout_at - time.time())
            }
            for req_id, p in self._pending.items()
        }

_confirmation_manager = ConfirmationManager()

def get_confirmation_manager() -> ConfirmationManager:
    return _confirmation_manager
