"""
Security Policy Evaluator for Raphael AI Assistant.
Checks commands and parameters against safety rules.
"""

from typing import Dict, Any, Tuple
from raphael.security.permissions import RiskLevel, SecurityPolicyMode
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("security.policy")

class SecurityPolicy:
    def __init__(self):
        self.config = get_config()

    def evaluate_tool_request(self, tool_name: str, risk_level: RiskLevel, args: Dict[str, Any]) -> Tuple[bool, bool, str]:
        """
        Returns (is_allowed, requires_confirmation, reason)
        """
        security_cfg = self.config.security

        # Check dangerous string patterns in arguments
        str_args = str(args).lower()
        for dangerous_kw in security_cfg.dangerous_keywords:
            if dangerous_kw in str_args:
                logger.warning(f"Blocked tool '{tool_name}' due to dangerous keyword '{dangerous_kw}' in args: {args}")
                return False, False, f"Blocked: Contains dangerous command pattern '{dangerous_kw}'"

        if risk_level == RiskLevel.CRITICAL:
            return False, False, "Blocked: Critical operations are disabled by policy"

        if risk_level == RiskLevel.HIGH_RISK and security_cfg.require_confirmation_for_high_risk:
            return True, True, "Requires confirmation due to HIGH_RISK operation"

        if risk_level == RiskLevel.MODERATE and security_cfg.require_confirmation_for_high_risk:
            # Check specific dangerous command args
            if tool_name == "run_command":
                cmd = args.get("command", "").strip()
                allowed_cmds = security_cfg.allowed_commands
                base_cmd = cmd.split()[0] if cmd else ""
                if base_cmd not in allowed_cmds:
                    return True, True, f"Command '{base_cmd}' is not on auto-approve whitelist"

        return True, False, "Auto-approved by policy"

_security_policy = SecurityPolicy()

def get_security_policy() -> SecurityPolicy:
    return _security_policy
