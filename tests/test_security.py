from raphael.security.policies import SecurityPolicy
from raphael.security.permissions import RiskLevel

def test_security_policy_dangerous_keyword():
    policy = SecurityPolicy()

    # Dangerous command should be blocked
    allowed, confirm, reason = policy.evaluate_tool_request("run_command", RiskLevel.HIGH_RISK, {"command": "rm -rf /"})
    assert allowed is False
    assert "Blocked" in reason

    # Safe command should be allowed
    allowed_safe, confirm_safe, reason_safe = policy.evaluate_tool_request("system_info", RiskLevel.READ_ONLY, {})
    assert allowed_safe is True
