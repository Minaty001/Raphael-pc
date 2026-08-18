"""
Wake Word Detector v3 for Raphael Always-Alive Runtime.

FIX 5 — Real KWS + audio ring buffer (Sections 11-14, 34-35).

Key capabilities:
  * Provider abstraction: pluggable wake-word engines.
      - PorcupineProvider  -> real on-device KWS (picovoice) when installed.
      - TranscriptWakeProvider -> lightweight phrase match on finalized STT
        segments (works with zero extra models; the default).
  * Audio ring buffer (Section 13): keeps the last N ms of *audio* so the
    words immediately after the wake phrase are never lost, even before STT
    catches up.
  * Wake phrase stripped from the captured command (Section 14).
  * State transitions pushed onto the AudioStateMachine (Section 11/36).
  * Fires a callback with the *remaining command* text for immediate capture.

Designed so the heavy STT model is only activated AFTER a wake is detected
(Section 34): low-power listening, then full capture.
"""

import re
import time
import wave
import io
import threading
from collections import deque
from typing import Callable, List, Optional, Tuple

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.voice.audio_state import AudioState, get_audio_state_machine

logger = get_logger("voice.wakeword")

DEFAULT_WAKE_WORDS = ["raphael", "hey raphael", "rafeal", "rapheal"]


class WakeWordProvider:
    """Base class for a pluggable wake-word engine."""

    name = "base"

    def initialize(self) -> bool:
        return True

    def process_audio(self, pcm: bytes) -> bool:
        """Return True if a wake word is detected in this audio chunk."""
        return False

    def process_transcript(self, text: str) -> Optional[str]:
        """Return the matched phrase if present in a finalized transcript."""
        return None

    def teardown(self) -> None:
        pass


class TranscriptWakeProvider(WakeWordProvider):
    """Lightweight phrase matcher over finalized STT segments.

    This is the default because it needs no extra model and still satisfies
    the spec: the mic/STT path is already pre-initialized (Section 12/13), so
    detection latency stays low.
    """

    name = "transcript"

    def __init__(self, wake_words: List[str]):
        self.wake_words = [w.lower().strip() for w in wake_words]

    def process_transcript(self, text: str) -> Optional[str]:
        clean = (text or "").lower().strip()
        # Prefer the longest matching phrase so "hey raphael" wins over "raphael".
        for kw in sorted(self.wake_words, key=len, reverse=True):
            if re.search(r"\b" + re.escape(kw) + r"\b", clean):
                return kw
        return None


class PorcupineProvider(WakeWordProvider):
    """Real on-device KWS via Picovoice Porcupine (if installed).

    Activated automatically when `pvporcupine` is importable and a keyword or
    access key is configured. Provides true low-power wake detection on audio.
    """

    name = "porcupine"

    def __init__(self, wake_words: List[str], access_key: str = "", keywords: Optional[List[str]] = None):
        self.wake_words = wake_words
        self.access_key = access_key
        self.keywords = keywords or ["raphael"]
        self._handle = None

    def initialize(self) -> bool:
        try:
            import pvporcupine  # type: ignore
            self._pv = pvporcupine
            self._handle = pvporcupine.create(
                access_key=self.access_key or None,
                keywords=self.keywords,
            )
            logger.info("Porcupine KWS initialized")
            return True
        except Exception as e:
            logger.warning(f"Porcupine unavailable, falling back to transcript KWS: {e}")
            return False

    def process_audio(self, pcm: bytes) -> bool:
        if not self._handle:
            return False
        try:
            import struct
            samples = struct.unpack_from("<%dh" % (len(pcm) // 2), pcm)
            for frame in samples:
                if self._handle.process(frame) >= 0:
                    return True
        except Exception as e:
            logger.error(f"Porcupine process error: {e}")
        return False

    def teardown(self):
        if self._handle:
            try:
                self._handle.delete()
            except Exception:
                pass
            self._handle = None


class AudioRingBuffer:
    """Fixed-duration audio ring buffer (Section 13) for pre-wake capture.

    Stores raw PCM chunks with timestamps; `collect_since(epoch)` returns the
    audio recorded from `epoch` onward (e.g. the moment the wake word fired),
    so the first ~1s after "Raphael" is preserved for STT.
    """

    def __init__(self, max_seconds: float = 2.0, sample_rate: int = 16000, width: int = 2):
        self.max_seconds = max_seconds
        self.sample_rate = sample_rate
        self.width = width
        self._chunks: deque = deque()
        self._lock = threading.Lock()

    def push(self, pcm: bytes, now: Optional[float] = None) -> None:
        now = now or time.time()
        with self._lock:
            self._chunks.append((now, pcm))
            cutoff = now - self.max_seconds
            while self._chunks and self._chunks[0][0] < cutoff:
                self._chunks.popleft()

    def collect_since(self, epoch: float) -> bytes:
        with self._lock:
            data = b"".join(p for t, p in self._chunks if t >= epoch)
        return data

    def collect_all(self) -> bytes:
        with self._lock:
            return b"".join(p for _, p in self._chunks)

    def to_wav(self, pcm: bytes) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.width)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()

    def clear(self) -> None:
        with self._lock:
            self._chunks.clear()


class WakeWordDetector:
    def __init__(self, wake_words: Optional[List[str]] = None, buffer_seconds: float = 1.0):
        config = get_config()
        self.wake_words = [w.lower().strip() for w in (wake_words or DEFAULT_WAKE_WORDS)]
        self.enabled = config.voice.wake_word_enabled
        self._buffer_seconds = buffer_seconds or config.wakeword.rolling_buffer_seconds
        # Transcript rolling buffer (Section 13): last ~buffer_seconds of text.
        self._buffer: deque = deque()
        self._on_wake_callback: Optional[Callable[[str], None]] = None
        self._last_wake_at = 0.0
        # Real audio ring buffer (Section 13).
        self.ring = AudioRingBuffer(max_seconds=self._buffer_seconds + 1.0,
                                    sample_rate=config.voice.sample_rate)
        self._provider = self._build_provider()

    def _build_provider(self) -> WakeWordProvider:
        cfg = get_config()
        porc = PorcupineProvider(
            self.wake_words,
            access_key=getattr(cfg.voice, "porcupine_key", "") or "",
            keywords=getattr(cfg.voice, "porcupine_keywords", None),
        )
        if porc.initialize():
            return porc
        return TranscriptWakeProvider(self.wake_words)

    # ------------------------------------------------------------------
    # Audio ingestion (real capture path, Section 12/13)
    # ------------------------------------------------------------------
    def ingest_audio(self, pcm: bytes) -> bool:
        """Feed a raw PCM chunk. Returns True if the KWS engine wakes."""
        if not self.enabled or not pcm:
            return False
        now = time.time()
        self.ring.push(pcm, now)
        if self._provider.process_audio(pcm):
            logger.info("Wake word detected via audio KWS")
            self._trigger(now, "")
            return True
        return False

    def get_post_wake_audio(self) -> bytes:
        """Return the audio captured in the ring buffer (for STT after wake)."""
        return self.ring.collect_all()

    # ------------------------------------------------------------------
    # Transcript ingestion (default low-power path)
    # ------------------------------------------------------------------
    def process_transcript_segment(self, text: str) -> bool:
        if not self.enabled or not text:
            return False

        now = time.time()
        self._push_segment(text, now)
        matched = self._provider.process_transcript(text)
        if matched:
            logger.info(f"Wake word detected: '{matched}'")
            self._trigger(now, matched)
            return True
        return False

    def _trigger(self, now: float, phrase: str) -> None:
        asm = get_audio_state_machine()
        asm.transition(AudioState.WAKE_DETECTED, f"wake:{phrase or 'audio'}")
        # Build the command = everything after the wake phrase, plus buffered
        # following speech (Section 13/14).
        command = self._strip_wake(self._buffer_text(), phrase) if phrase else self._buffer_text()
        self._last_wake_at = now
        if self._on_wake_callback:
            self._on_wake_callback(command)

    # ------------------------------------------------------------------
    # Rolling text buffer (Section 13)
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

    def _find_wake(self, text: str) -> Optional[str]:
        clean = (text or "").lower().strip()
        for kw in sorted(self.wake_words, key=len, reverse=True):
            if re.search(r"\b" + re.escape(kw) + r"\b", clean):
                return kw
        return None

    def _strip_wake(self, text: str, phrase: str) -> str:
        if not phrase:
            return text.strip()
        # Strip the matched phrase wherever it appears (not just at start, since a
        # longer variant like "hey raphael" may have already been reduced to its
        # shorter match "raphael" which sits mid-string after a prefix).
        pattern = re.compile(r"\s*\b" + re.escape(phrase) + r"\b\s*[,:]?", re.IGNORECASE)
        stripped = pattern.sub(" ", text).strip()
        # Also drop a leading invocation prefix if one remains (e.g. "hey", "ok").
        stripped = re.sub(r"^(hey|ok|yo|hi)\s+", "", stripped, flags=re.IGNORECASE)
        return stripped

    # API used by AlwaysAliveController
    def is_wake_in_text(self, text: str) -> bool:
        return self._find_wake(text) is not None

    def strip_wake(self, text: str) -> str:
        phrase = self._find_wake(text)
        return self._strip_wake(text, phrase) if phrase else text

    def set_on_wake(self, callback: Callable[[str], None]) -> None:
        self._on_wake_callback = callback

    def teardown(self) -> None:
        try:
            self._provider.teardown()
        except Exception:
            pass


_wake_word_detector = WakeWordDetector()


def get_wake_word_detector() -> WakeWordDetector:
    return _wake_word_detector


def get_wakeword_detector() -> WakeWordDetector:
    return _wake_word_detector
