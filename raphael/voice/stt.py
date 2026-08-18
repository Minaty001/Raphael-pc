"""
Speech-To-Text (STT) Provider Interface for Raphael AI Assistant.
Supports Sherpa-ONNX, Web Speech API client payload, and fallback engines.
"""

from abc import ABC, abstractmethod
from typing import Optional
from raphael.core.logging import get_logger

logger = get_logger("voice.stt")

class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: bytes) -> str:
        pass

class MockSTTProvider(STTProvider):
    def transcribe(self, audio_data: bytes) -> str:
        return "Hey Raphael, what is the system status?"

def get_stt_provider() -> STTProvider:
    return MockSTTProvider()
