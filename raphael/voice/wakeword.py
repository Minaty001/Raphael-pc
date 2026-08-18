"""
Wake Word Detector for Raphael v3.
Supports wake word variants: 'Raphael', 'Hey Raphael', 'Rafeal', 'Rapheal'.
Uses local audio stream processing fallback with low CPU idle overhead.
"""

import time
import re
from typing import Callable, Optional, List
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("voice.wakeword")

DEFAULT_WAKE_WORDS = ["raphael", "hey raphael", "rafeal", "rapheal"]

class WakeWordDetector:
    def __init__(self, wake_words: Optional[List[str]] = None):
        config = get_config()
        self.wake_words = [w.lower() for w in (wake_words or DEFAULT_WAKE_WORDS)]
        self.enabled = config.voice.wake_word_enabled
        self._callback: Optional[Callable[[], None]] = None

    def set_callback(self, callback: Callable[[], None]) -> None:
        self._callback = callback

    def process_transcript_segment(self, text: str) -> bool:
        """
        Inspects an STT text stream for any wake word variant matches.
        """
        if not self.enabled:
            return False

        clean_text = text.lower().strip()
        for kw in self.wake_words:
            if re.search(r'\b' + re.escape(kw) + r'\b', clean_text):
                logger.info(f"Wake word detected: '{kw}' in '{text}'")
                if self._callback:
                    self._callback()
                return True
        return False

_wake_word_detector = WakeWordDetector()

def get_wake_word_detector() -> WakeWordDetector:
    return _wake_word_detector

def get_wakeword_detector() -> WakeWordDetector:
    return _wake_word_detector
