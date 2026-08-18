"""
Text-To-Speech (TTS) Provider Interface for Raphael AI Assistant.
Supports web client synthesis triggers, Sherpa-ONNX, and pyttsx3/espeak fallbacks.
"""

import asyncio
from abc import ABC, abstractmethod
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus

logger = get_logger("voice.tts")

class TTSProvider(ABC):
    @abstractmethod
    async def speak(self, text: str) -> None:
        pass

class WebClientTTSProvider(TTSProvider):
    async def speak(self, text: str) -> None:
        bus = get_event_bus()
        await bus.publish("voice.tts.started", {"text": text}, source="tts_provider")
        logger.info(f"TTS triggered for text: '{text[:50]}...'")
        # Estimate duration for event completion
        estimated_duration = max(1.0, len(text) * 0.06)
        await asyncio.sleep(estimated_duration)
        await bus.publish("voice.tts.completed", {"text": text}, source="tts_provider")

_tts_provider = WebClientTTSProvider()

def get_tts_provider() -> TTSProvider:
    return _tts_provider
