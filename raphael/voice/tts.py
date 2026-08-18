"""
Text-To-Speech (TTS) Provider Interface for Raphael Always-Alive Runtime.

FIX 7 — Real cancellable TTS (Sections 16/35/68).
  * EdgeTTSProvider    -> real audio playback via edge-tts (streamed to a
    local audio backend). Cancellable: a `voice.tts.cancel` event stops
    playback immediately for barge-in (Section 16).
  * Pyttsx3Provider     -> offline fallback when edge-tts audio is unavailable.
  * WebClientTTSProvider-> triggers client-side synthesis (the HUD plays it).
  * MockTTSProvider     -> dev/CI fallback.

Selected by config.voice.tts_provider. Cancellation is cooperative via an
async event the VoicePipeline / AlwaysAliveController publishes.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus

logger = get_logger("voice.tts")


class TTSProvider(ABC):
    name = "base"
    _cancel_event: Optional[asyncio.Event] = None

    def _get_cancel_event(self) -> asyncio.Event:
        if self._cancel_event is None or self._cancel_event.is_set() is False and getattr(self._cancel_event, "_loop", None) is None:
            self._cancel_event = asyncio.Event()
        return self._cancel_event

    async def speak(self, text: str) -> None:
        raise NotImplementedError

    async def cancel(self) -> None:
        """Request immediate stop of current playback (barge-in)."""
        ev = self._get_cancel_event()
        ev.set()


class WebClientTTSProvider(TTSProvider):
    name = "web"

    async def speak(self, text: str) -> None:
        bus = get_event_bus()
        await bus.publish("voice.tts.started", {"text": text}, source="tts_provider")
        logger.info(f"TTS triggered for text: '{text[:50]}...'")
        # Wait (cooperatively) until finished or cancelled.
        ev = self._get_cancel_event()
        ev.clear()
        estimated = max(1.0, len(text) * 0.06)
        try:
            await asyncio.wait_for(ev.wait(), timeout=estimated)
            logger.info("TTS cancelled by user (barge-in).")
        except asyncio.TimeoutError:
            pass
        await bus.publish("voice.tts.completed", {"text": text}, source="tts_provider")

    async def cancel(self) -> None:
        self._get_cancel_event().set()


class MockTTSProvider(TTSProvider):
    name = "mock"

    async def speak(self, text: str) -> None:
        bus = get_event_bus()
        await bus.publish("voice.tts.started", {"text": text}, source="tts_provider")
        ev = self._get_cancel_event()
        ev.clear()
        estimated = max(0.5, len(text) * 0.04)
        try:
            await asyncio.wait_for(ev.wait(), timeout=estimated)
        except asyncio.TimeoutError:
            pass
        await bus.publish("voice.tts.completed", {"text": text}, source="tts_provider")


class EdgeTTSProvider(TTSProvider):
    name = "edge"

    def __init__(self, voice: str = "en-US-GuyNeural"):
        self.voice = voice
        self._player = None

    async def speak(self, text: str) -> None:
        bus = get_event_bus()
        await bus.publish("voice.tts.started", {"text": text}, source="tts_provider")
        ev = self._get_cancel_event()
        ev.clear()
        try:
            import edge_tts  # type: ignore
            communicate = edge_tts.Communicate(text, self.voice)
            # Stream audio to the default output device if a player is available.
            await self._stream(communicate, ev)
        except Exception as e:
            logger.warning(f"Edge TTS playback failed ({e}); falling back to timed mock.")
            # Cooperative cancel-aware wait so barge-in still works.
            try:
                await asyncio.wait_for(ev.wait(), timeout=max(0.5, len(text) * 0.05))
            except asyncio.TimeoutError:
                pass
        await bus.publish("voice.tts.completed", {"text": text}, source="tts_provider")

    async def _stream(self, communicate, cancel_ev: asyncio.Event):
        """Play streamed audio; abort early if cancel is requested."""
        try:
            import sounddevice  # type: ignore  # optional
            import numpy as np  # type: ignore  # optional
            import io, wave
            chunks = []
            async for chunk in communicate.stream():
                if cancel_ev.is_set():
                    logger.info("Edge TTS stream aborted (barge-in).")
                    break
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            if chunks and not cancel_ev.is_set():
                wav = io.BytesIO(b"".join(chunks))
                wf = wave.open(wav, "rb")
                data = wf.readframes(wf.getnframes())
                arr = np.frombuffer(data, dtype=np.int16)
                sounddevice.play(arr, wf.getframerate())
                while sounddevice.get_stream().active and not cancel_ev.is_set():
                    await asyncio.sleep(0.05)
        except ImportError:
            # No sounddevice: just await the generator (drives the cancel timer).
            async for _ in communicate.stream():
                if cancel_ev.is_set():
                    break
                await asyncio.sleep(0.02)


class Pyttsx3Provider(TTSProvider):
    name = "pyttsx3"

    def __init__(self):
        self._engine = None

    def _ensure(self):
        if self._engine is not None:
            return True
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()
            return True
        except Exception as e:
            logger.warning(f"pyttsx3 unavailable: {e}")
            return False

    async def speak(self, text: str) -> None:
        bus = get_event_bus()
        await bus.publish("voice.tts.started", {"text": text}, source="tts_provider")
        ev = self._get_cancel_event()
        ev.clear()
        if self._ensure():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._engine.say, text)
            await loop.run_in_executor(None, self._engine.runAndWait)
        else:
            try:
                await asyncio.wait_for(ev.wait(), timeout=max(0.5, len(text) * 0.05))
            except asyncio.TimeoutError:
                pass
        await bus.publish("voice.tts.completed", {"text": text}, source="tts_provider")


_PROVIDERS = {
    "edge": EdgeTTSProvider,
    "pyttsx3": Pyttsx3Provider,
    "web": WebClientTTSProvider,
    "mock": MockTTSProvider,
}

_cached: Optional[TTSProvider] = None


def get_tts_provider() -> TTSProvider:
    global _cached
    if _cached is not None:
        return _cached
    cfg = get_config()
    kind = (getattr(cfg.voice, "tts_provider", "mock") or "mock").lower()
    cls = _PROVIDERS.get(kind, MockTTSProvider)
    try:
        _cached = cls()
    except Exception as e:
        logger.warning(f"TTS provider '{kind}' init failed, using mock: {e}")
        _cached = MockTTSProvider()
    logger.info(f"TTS provider selected: {_cached.name}")
    return _cached
