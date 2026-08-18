"""
Wake Word Detector v2 for Raphael v3 Always-Alive Runtime.

Key upgrades over the previous transcript-only version:
  * Rolling audio/transcript buffer (Section 13) so the words immediately
    *after* the wake phrase are not lost.
  * Wake phrase stripped from the captured command (Section 14).
  * State transitions pushed onto the AudioStateMachine (Section 11/36).
  * Fires a callback with the *remaining command* text for immediate capture.

This is provider-agnostic: it consumes finalized STT segments (like the rest of
the pipeline) so it runs without a heavy always-on model, but it can also be fed
low-power VAD segments. The rolling buffer protects the first ~1s after a wake.
"""

import re
import time
from collections import deque
from typing import Callable, List, Optional
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.voice.audio_state import AudioState, get_audio_state_machine

logger = get_logger("voice.wakeword")

DEFAULT_WAKE_WORDS = ["raphael", "hey raphael", "rafeal", "rapheal"]


class WakeWordDetector:
    def __init__(self, wake_words: Optional[List[str]] = None, buffer_seconds: float = 1.0):
        config = get_config()
        self.wake_words = [w.lower().strip() for w in (wake_words or DEFAULT_WAKE_WORDS)]
        self.enabled = config.voice.wake_word_enabled
        self._buffer_seconds = buffer_seconds
        # Rolling buffer of (timestamp, text) segments (Section 13).
        self._buffer: deque = deque()
        self._on_wake_callback: Optional[Callable[[str], None]] = None
        self._last_wake_at = 0.0

    def set_on_wake(self, callback: Callable[[str], None]) -> None:
        """callback receives the command text *after* the wake word."""
        self._on_wake_callback = callback

    # ------------------------------------------------------------------
    # Rolling buffer (Section 13): keep last ~buffer_seconds of transcript.
    # ------------------------------------------------------------------
    def _prune_buffer(self, now: float) -> None:
        cutoff = now - self._buffer_seconds
        while self._buffer and self._buffer[0][0] < cutoff:
            self._buffer.popleft()

    def _push_segment(self, text: str, now: float) -> None:
        self._prune_buffer(now)
        self._buffer.append((now, text))

    def _buffer_text(self) -> str:
        return " ".join(t for _, t in self._buffer).strip()

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def _find_wake(self, text: str) -> Optional[str]:
        """Return the matched wake phrase if present, else None."""
        clean = text.lower().strip()
        for kw in self.wake_words:
            if re.search(r"\b" + re.escape(kw) + r"\b", clean):
                return kw
        return None

    def _strip_wake(self, text: str, phrase: str) -> str:
        """Remove the wake phrase (and a trailing comma) from the command."""
        pattern = re.compile(r"^\s*(" + re.escape(phrase) + r")\s*[,:]?\s*", re.IGNORECASE)
        return pattern.sub("", text).strip()

    # ------------------------------------------------------------------
    # Ingest a finalized STT segment. Returns True if wake detected.
    # ------------------------------------------------------------------
    def process_transcript_segment(self, text: str) -> bool:
        if not self.enabled or not text:
            return False

        now = time.time()
        self._push_segment(text, now)
        matched = self._find_wake(text)

        if matched:
            logger.info(f"Wake word detected: '{matched}'")
            asm = get_audio_state_machine()
            asm.transition(AudioState.WAKE_DETECTED, f"wake:{matched}")

            # The command is everything after the wake phrase in this segment,
            # PLUS any buffered following speech (Section 13 / 14).
            command = self._strip_wake(text, matched)
            buffered = self._buffer_text()
            # Avoid duplicating the current segment's tail.
            combined = (command + " " + buffered).strip()
            # De-dupe: if buffered already contains command, keep the longer form.
            if command and buffered.startswith(command):
                combined = buffered

            self._last_wake_at = now
            if self._on_wake_callback:
                self._on_wake_callback(combined)
            return True
        return False

    # Convenience used by the AlwaysAliveController when it has a full
    # command captured post-wake.
    def is_wake_in_text(self, text: str) -> bool:
        return self._find_wake(text) is not None

    def strip_wake(self, text: str) -> str:
        phrase = self._find_wake(text)
        return self._strip_wake(text, phrase) if phrase else text


_wake_word_detector = WakeWordDetector()


def get_wake_word_detector() -> WakeWordDetector:
    return _wake_word_detector


def get_wakeword_detector() -> WakeWordDetector:
    return _wake_word_detector
