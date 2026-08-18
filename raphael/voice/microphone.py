"""
Microphone capture source for Raphael v3 Always-Alive Runtime (FIX 4 / FIX 5).

FEEDS the voice pipeline with REAL audio:
  * Raw PCM is pushed to the WakeWordDetector ring buffer (FIX 5) so the
    words right after "Raphael" are never lost.
  * When the runtime is in COMMAND_LISTENING (Section 11/13/14) the captured
    audio is handed to the configured STT provider (FIX 6).

The capture source is OPTIONAL and defensive: it uses `sounddevice` when
available and silently disables itself otherwise (e.g. a headless server or a
machine without audio libs). This keeps the always-alive runtime alive and
functional even where no microphone is present — the WebSocket/browser path
(Web Speech) still works regardless.
"""

import asyncio
import threading
import time
from typing import Optional

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.voice.audio_state import get_audio_state_machine, AudioState

logger = get_logger("voice.microphone")


class MicrophoneSource:
    """Chooses a capture backend and streams PCM frames to the wake detector."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, block_ms: int = 30):
        cfg = get_config()
        self.sample_rate = cfg.voice.sample_rate or sample_rate
        self.channels = channels
        self.block_ms = block_ms
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sd = None
        self._available = self._probe()
        self._asm = get_audio_state_machine()

    # ------------------------------------------------------------------
    def _probe(self) -> bool:
        """Return True if a capture backend is importable."""
        try:
            import sounddevice as sd  # type: ignore
            self._sd = sd
            return True
        except Exception as e:
            logger.info(f"Microphone capture disabled (no audio backend: {e})")
            return False

    @property
    def available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------
    async def start(self) -> None:
        if not self._available or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, name="raphael-mic", daemon=True)
        self._thread.start()
        logger.info("Microphone capture started (real audio -> wake detector).")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        logger.info("Microphone capture stopped.")

    # ------------------------------------------------------------------
    def _capture_loop(self) -> None:
        """Pull PCM frames on a worker thread; dispatch to wake/STT on the loop."""
        try:
            sd = self._sd
            block = int(self.sample_rate * self.block_ms / 1000)

            def _callback(indata, frames, time_info, status):
                if not self._running:
                    return
                pcm = indata.tobytes()
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    return
                if not loop.is_running():
                    return
                loop.call_soon_threadsafe(self._dispatch, pcm)

            with sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=block,
                callback=_callback,
            ):
                while self._running:
                    time.sleep(0.05)
        except Exception as e:
            logger.warning(f"Microphone capture loop error: {e}")
            self._running = False

    def _dispatch(self, pcm: bytes) -> None:
        """Route a captured PCM frame to the right consumer (FIX 4/5/6)."""
        from raphael.voice.wakeword import get_wake_word_detector
        from raphael.voice.stt import get_stt_provider

        wwd = get_wake_word_detector()
        # Always feed the ring buffer / KWS so a wake is detected (FIX 5).
        wwd.ingest_audio(pcm)

        # If we are actively capturing a command, run STT on this frame (FIX 6).
        if self._asm.state == AudioState.COMMAND_LISTENING:
            asyncio.ensure_future(self._transcribe(pcm, get_stt_provider()))

    async def _transcribe(self, pcm: bytes, stt) -> None:
        try:
            text = await stt.transcribe(pcm)
            if text and text.strip():
                from raphael.voice.pipeline import get_voice_pipeline
                await get_voice_pipeline().handle_speech_input(text, is_final=True)
        except Exception as e:
            logger.warning(f"Mic STT error: {e}")


_mic_source = MicrophoneSource()


def get_microphone() -> MicrophoneSource:
    return _mic_source
