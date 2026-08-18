"""
Voice Pipeline Coordinator for Raphael AI Assistant.
Orchestrates audio capture, VAD, wake word detection, STT transcription, and TTS playback events.
"""

import asyncio
from typing import Optional
from raphael.core.state_manager import get_state_manager, AssistantState
from raphael.core.event_bus import get_event_bus
from raphael.voice.wakeword import get_wakeword_detector
from raphael.brain.reasoning import get_reasoning_engine
from raphael.core.logging import get_logger

logger = get_logger("voice.pipeline")

class VoicePipeline:
    def __init__(self):
        self._listening = False

    async def start_listening(self) -> None:
        if self._listening:
            return
        self._listening = True
        state_mgr = get_state_manager()
        bus = get_event_bus()

        await state_mgr.set_state(AssistantState.LISTENING)
        await bus.publish("voice.capture.started", {}, source="voice_pipeline")
        logger.info("Voice pipeline listening started.")

    async def stop_listening(self) -> None:
        if not self._listening:
            return
        self._listening = False
        state_mgr = get_state_manager()
        bus = get_event_bus()

        await bus.publish("voice.capture.stopped", {}, source="voice_pipeline")
        await state_mgr.set_state(AssistantState.IDLE)
        logger.info("Voice pipeline listening stopped.")

    async def handle_speech_input(self, transcript: str, is_final: bool = True) -> None:
        bus = get_event_bus()
        state_mgr = get_state_manager()
        wakeword = get_wakeword_detector()

        if not is_final:
            await bus.publish("voice.stt.partial", {"text": transcript}, source="voice_pipeline")
            return

        await bus.publish("voice.stt.completed", {"text": transcript}, source="voice_pipeline")
        logger.info(f"Final transcript received: '{transcript}'")

        # Check wake word
        if wakeword.check_phrase(transcript):
            await state_mgr.set_state(AssistantState.WAKE_DETECTED, {"phrase": transcript})
            await bus.publish("voice.wake.detected", {"text": transcript}, source="voice_pipeline")
            await asyncio.sleep(0.3)

        # Process user input in reasoning engine
        reasoning = get_reasoning_engine()
        await reasoning.process_user_input(transcript)

_voice_pipeline = VoicePipeline()

def get_voice_pipeline() -> VoicePipeline:
    return _voice_pipeline
