"""
Metacognition & Uncertainty Engine for Raphael AI Assistant.
Tracks what Raphael knows, assumes, or is uncertain about.
"""

from typing import Dict, Any, List
from raphael.core.logging import get_logger

logger = get_logger("brain.metacognition")

class UncertaintyStatus:
    KNOWN = "KNOWN"
    LIKELY = "LIKELY"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"

class MetaCognitionEngine:
    def evaluate_belief(self, claim: str, confidence: float, evidence: List[str]) -> Dict[str, Any]:
        if confidence >= 0.9:
            status = UncertaintyStatus.KNOWN
            needs_confirm = False
        elif confidence >= 0.7:
            status = UncertaintyStatus.LIKELY
            needs_confirm = False
        elif confidence >= 0.4:
            status = UncertaintyStatus.POSSIBLE
            needs_confirm = True
        else:
            status = UncertaintyStatus.UNKNOWN
            needs_confirm = True

        return {
            "claim": claim,
            "confidence": confidence,
            "status": status,
            "evidence": evidence,
            "needs_confirmation": needs_confirm
        }

    def evaluate_uncertainty(self, text: str, facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        conf = 0.9 if len(facts) > 0 else 0.5
        status = UncertaintyStatus.KNOWN if conf >= 0.8 else UncertaintyStatus.POSSIBLE
        return {
            "query": text,
            "status": status,
            "confidence": conf,
            "evidence_facts_count": len(facts)
        }

_metacognition_engine = MetaCognitionEngine()

def get_metacognition_engine() -> MetaCognitionEngine:
    return _metacognition_engine

def get_meta_cognition() -> MetaCognitionEngine:
    return _metacognition_engine
