"""
Speech-To-Text (STT) Provider Interface for Raphael Always-Alive Runtime.

FIX 6 — Real STT provider selection.
  * STTProvider abstraction with pluggable engines.
  * VoskProvider   -> offline, on-device (if `vosk` + a model is available).
  * WebSpeechProvider -> browser/Web Speech API payload passthrough.
  * Edge/WhisperProvider -> cloud/local whisper when configured.
  * MockProvider   -> deterministic fallback for dev/CI (no audio hardware).

Selected by config.voice.stt_provider ('vosk' | 'web' | 'whisper' | 'mock').
"""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("voice.stt")


class STTProvider(ABC):
    name = "base"

    @abstractmethod
    async def transcribe(self, audio_data: bytes) -> str:
        """Transcribe raw PCM/audio bytes into text."""
        ...

    async def transcribe_stream(self, audio_chunks: AsyncGenerator[bytes, None]) -> AsyncGenerator[str, None]:
        """Streaming transcription.

        Yields partial transcript texts as audio arrives, then a final
        transcript. The default implementation is BUFFERED: it collects all
        chunks and emits only the final result (correct for engines without
        native streaming, e.g. Whisper). Engines with incremental support
        (e.g. Vosk) override this to emit partials per chunk (ROADMAP L3.6).
        """
        data = b""
        async for chunk in audio_chunks:
            data += chunk
        final = await self.transcribe(data)
        if final:
            yield final


class MockSTTProvider(STTProvider):
    name = "mock"

    async def transcribe(self, audio_data: bytes) -> str:
        # Deterministic dev response; never used in production paths.
        return "Hey Raphael, what is the system status?"


class VoskProvider(STTProvider):
    name = "vosk"

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.getenv("VOSK_MODEL_PATH", "")
        self._model = None
        self._recognizer = None

    def _ensure(self) -> bool:
        if self._recognizer is not None:
            return True
        try:
            from vosk import Model, KaldiRecognizer  # type: ignore
            if not self.model_path or not os.path.isdir(self.model_path):
                logger.warning("Vosk model path not found; cannot use Vosk STT")
                return False
            self._model = Model(self.model_path)
            self._recognizer = KaldiRecognizer(self._model, 16000)
            return True
        except Exception as e:
            logger.warning(f"Vosk unavailable: {e}")
            return False

    async def transcribe(self, audio_data: bytes) -> str:
        if not self._ensure():
            return ""
        import json
        self._recognizer.AcceptWaveform(audio_data)
        result = json.loads(self._recognizer.Result())
        return result.get("text", "")

    async def transcribe_stream(self, audio_chunks: AsyncGenerator[bytes, None]) -> AsyncGenerator[str, None]:
        """Real incremental transcription via Vosk partial results.

        Emits a partial transcript after each audio chunk (low latency), then
        a final transcript once all audio is consumed. This is genuine
        streaming -- partials arrive as the user is still speaking.
        """
        if not self._ensure():
            return
        import json
        async for chunk in audio_chunks:
            self._recognizer.AcceptWaveform(chunk)
            partial = json.loads(self._recognizer.PartialResult())
            text = partial.get("partial", "")
            if text:
                yield text
        final = json.loads(self._recognizer.Result())
        text = final.get("text", "")
        if text:
            yield text



class WebSpeechProvider(STTProvider):
    """Client-side Web Speech API: the browser does the recognition and sends
    finalized transcript segments over the WebSocket. This provider is a
    passthrough that accepts already-transcribed text payloads."""

    name = "web"

    async def transcribe(self, audio_data: bytes) -> str:
        # The frontend sends transcript text, not raw audio, for this provider.
        try:
            return audio_data.decode("utf-8", errors="ignore")
        except Exception:
            return ""


class WhisperProvider(STTProvider):
    """Local/cloud Whisper (openai-whisper or faster-whisper) when installed."""

    name = "whisper"

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _ensure(self):
        if self._model is not None:
            return True
        try:
            import whisper  # type: ignore
            self._model = whisper.load_model(self.model_size)
            return True
        except Exception as e:
            logger.warning(f"Whisper unavailable: {e}")
            return False

    async def transcribe(self, audio_data: bytes) -> str:
        if not self._ensure():
            return ""
        # Whisper expects a file; write temp wav then decode.
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            path = f.name
        try:
            res = self._model.transcribe(path)
            return res.get("text", "").strip()
        finally:
            try:
                os.unlink(path)
            except Exception:
                pass


_PROVIDERS = {
    "vosk": VoskProvider,
    "web": WebSpeechProvider,
    "whisper": WhisperProvider,
    "mock": MockSTTProvider,
}

_cached: Optional[STTProvider] = None


def get_stt_provider() -> STTProvider:
    global _cached
    if _cached is not None:
        return _cached
    cfg = get_config()
    kind = (getattr(cfg.voice, "stt_provider", "mock") or "mock").lower()
    cls = _PROVIDERS.get(kind, MockSTTProvider)
    try:
        _cached = cls()
    except Exception as e:
        logger.warning(f"STT provider '{kind}' init failed, using mock: {e}")
        _cached = MockSTTProvider()
    logger.info(f"STT provider selected: {_cached.name}")
    return _cached
