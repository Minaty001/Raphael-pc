"""
Tool Registry for Raphael AI Assistant.
Provides decorator for defining tools with risk levels, parameter validation, and safe execution.
"""

import time
import inspect
import asyncio
from typing import Dict, Any, Callable, Awaitable, List, Optional
from raphael.security.permissions import RiskLevel
from raphael.security.policies import get_security_policy
from raphael.security.confirmation import get_confirmation_manager
from raphael.security.audit import get_audit_logger
from raphael.platform.common import make_action_result
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus

logger = get_logger("tool.registry")

class Tool:
    def __init__(self, name: str, description: str, risk_level: RiskLevel, func: Callable):
        self.name = name
        self.description = description
        self.risk_level = risk_level
        self.func = func
        self.signature = inspect.signature(func)

    async def execute(self, user_request: Optional[str] = None, intent: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        start_time = time.time()
        bus = get_event_bus()

        await bus.publish("tool.started", {"tool": self.name, "args": kwargs}, source="tool_registry")

        # 1. Policy check
        policy = get_security_policy()
        allowed, requires_confirm, reason = policy.evaluate_tool_request(self.name, self.risk_level, kwargs)

        if not allowed:
            duration = (time.time() - start_time) * 1000
            res = make_action_result(self.name, "denied", duration, error=reason)
            get_audit_logger().log_action(self.name, kwargs, self.risk_level.value, "denied", user_request, intent, error=reason, duration_ms=duration)
            await bus.publish("tool.failed", res, source="tool_registry")
            return res

        # 2. Confirmation check
        if requires_confirm:
            confirmed = await get_confirmation_manager().request_confirmation(self.name, kwargs, reason)
            if not confirmed:
                duration = (time.time() - start_time) * 1000
                res = make_action_result(self.name, "denied", duration, error="Operation cancelled by user confirmation policy")
                get_audit_logger().log_action(self.name, kwargs, self.risk_level.value, "denied", user_request, intent, error="Cancelled by user", duration_ms=duration)
                await bus.publish("tool.failed", res, source="tool_registry")
                return res

        # 3. Execution
        try:
            if asyncio.iscoroutinefunction(self.func):
                result = await self.func(**kwargs)
            else:
                result = await asyncio.to_thread(self.func, **kwargs)

            duration = (time.time() - start_time) * 1000

            # Standardize output if not already formatted
            if isinstance(result, dict) and "action" in result and "status" in result:
                res = result
            else:
                res = make_action_result(self.name, "success", duration, result=result)

            get_audit_logger().log_action(self.name, kwargs, self.risk_level.value, res.get("status", "success"), user_request, intent, result=res.get("result"), error=res.get("error"), duration_ms=duration)
            await bus.publish("tool.completed", res, source="tool_registry")
            return res

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            logger.error(f"Error executing tool '{self.name}': {e}", exc_info=True)
            res = make_action_result(self.name, "failed", duration, error=str(e))
            get_audit_logger().log_action(self.name, kwargs, self.risk_level.value, "failed", user_request, intent, error=str(e), duration_ms=duration)
            await bus.publish("tool.failed", res, source="tool_registry")
            return res

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str, risk_level: RiskLevel = RiskLevel.LOW_RISK):
        def decorator(func: Callable):
            tool = Tool(name, description, risk_level, func)
            self._tools[name] = tool
            logger.info(f"Registered tool: {name} [{risk_level.value}]")
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    async def execute_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        tool = self.get_tool(name)
        if not tool:
            return {"action": name, "status": "failed", "error": f"Tool '{name}' not registered", "duration_ms": 0.0}
        return await tool.execute(**(args or {}))

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "risk_level": t.risk_level.value,
                "parameters": [p.name for p in t.signature.parameters.values()]
            }
            for t in self._tools.values()
        ]

_tool_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    return _tool_registry
