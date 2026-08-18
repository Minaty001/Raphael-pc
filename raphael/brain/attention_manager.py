"""
Attention Manager for Raphael AI Assistant.
Filters and ranks environmental signals by urgency, relevance, and task relation.
"""

from typing import Dict, Any, List
from raphael.core.logging import get_logger

logger = get_logger("brain.attention")

class AttentionManager:
    def rank_signal(self, signal: Dict[str, Any], current_goal: str = "") -> float:
        """
        Calculates an attention score between 0.0 (ignore) and 1.0 (critical focus).
        """
        source = signal.get("source", "")
        payload = signal.get("payload", {})
        
        score = 0.3  # Base baseline

        # User voice input is highest priority
        if source == "voice":
            return 1.0

        # Build errors or exception alerts are high priority
        if payload.get("visible_error"):
            score += 0.5

        # Active coding activity when current goal is development
        activity = payload.get("activity", "")
        if "Coding" in activity or "Development" in activity:
            score += 0.3

        # Minor browser background changes get low score
        if "Browsing" in activity and not payload.get("visible_error"):
            score -= 0.1

        final_score = max(0.0, min(1.0, score))
        logger.debug(f"Attention score for signal {source}: {final_score:.2f}")
        return final_score

_attention_manager = AttentionManager()

def get_attention_manager() -> AttentionManager:
    return _attention_manager
