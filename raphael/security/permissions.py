"""
Security Permission Levels for Raphael AI Assistant.
"""

from enum import Enum

class RiskLevel(str, Enum):
    READ_ONLY = "READ_ONLY"      # System info, status, help
    LOW_RISK = "LOW_RISK"        # Volume control, open app, browser launch
    MODERATE = "MODERATE"        # File creation, clipboard write, application kill
    HIGH_RISK = "HIGH_RISK"      # File delete, shell command execution, system configuration
    CRITICAL = "CRITICAL"        # Disk partition, system format, registry wipe (Blocked by default)

class SecurityPolicyMode(str, Enum):
    PERMISSIVE = "PERMISSIVE"
    BALANCED = "BALANCED"
    STRICT = "STRICT"
