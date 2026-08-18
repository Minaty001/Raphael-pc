"""
Voice Pipeline Coordinator for Raphael Always-Alive Runtime.

FIX 4 — Voice pipeline integration (Sections 11-16, 35, 68).
  * Bridges raw/transcribed speech into the Always-Alive controller.
  * Drives the AudioStateMachine (wake -> command -> processing -> speaking).
  * Uses the real STT + TTS providers (FIX 6 / FIX 7).
  * Handles barge-in: subscribes to `voice.tts.cancel` so a user interrupt
    stops TTS and returns to listening (Section 16).
"""

import asyncio
from typing import Optional

from raphael.core.state_manager import get_state_manager, AssistantState
from raphael.core.event_bus import get_event_bus
from raphael.voice.audio_state import AudioState, get_audio_state_machine
from raphael.voice.wakeword import get_wake_word_detector
from raphael.voice.stt import get_stt_provider
from raphael.voice.tts import get_tts_provider
from raphael.voice.pipeline_helpers import run_command  # shared command runner
from raphael.core.logging import get_logger

logger = get_logger("voice.pipeline")


class VoicePipeline:
    def __init__(self):
        self._listening = False
        self._asm = get_audio_state_machine()
        self._subscribed = False

    def _ensure_subscribed(self):
        if not self._subscribed:
            get_event_bus().subscribe("voice.tts.cancel", self._on_tts_cancel)
            self._subscribed = True

    async def start_listening(self) -> None:
        if self._listening:
            return
        self._listening = True
        self._ensure_subscribed()
        self._asm.transition(AudioState.WAKE_LISTENING, "pipeline start")
        await get_state_manager().set_state(AssistantState.LISTENING)
        await get_event_bus().publish("voice.capture.started", {}, source="voice_pipeline")
        logger.info("Voice pipeline listening started (wake-listening).")

    async def stop_listening(self) -> None:
        if not self._listening:
            return
        self._listening = False
        self._asm.transition(AudioState.AUDIO_IDLE, "pipeline stop")
        await get_state_manager().set_state(AssistantState.IDLE)
        await get_event_bus().publish("voice.capture.stopped", {}, source="voice_pipeline")
        logger.info("Voice pipeline listening stopped.")

    # ------------------------------------------------------------------
    # Speech ingestion
    # ------------------------------------------------------------------
    async def handle_speech_input(self, transcript: str, is_final: bool = True) -> None:
        bus = get_event_bus()
        if not is_final:
            await bus.publish("voice.stt.partial", {"text": transcript}, source="voice_pipeline")
            return

        await bus.publish("voice.stt.completed", {"text": transcript}, source="voice_pipeline")
        logger.info(f"Final transcript: '{transcript}'")

        wwd = get_wake_word_detector()
        has_wake = wwd.is_wake_in_text(transcript)
        in_command_mode = self._asm.state == AudioState.COMMAND_LISTENING

        # Check continuous conversation window from AlwaysAliveController
        in_conv_window = False
        try:
            from raphael.runtime.always_alive import get_always_alive
            in_conv_window = get_always_alive().in_conversation_window()
        except Exception:
            pass

        if has_wake:
            command = wwd.strip_wake(transcript)
            if not command or not command.strip():
                # User spoke only the wake phrase (e.g. "Raphael" / "Hey Raphael")
                logger.info("Wake word detected without follow-up command. Entering COMMAND_LISTENING.")
                self._asm.transition(AudioState.WAKE_DETECTED, "wake word detected")
                self._asm.transition(AudioState.COMMAND_LISTENING, "listening for command after wake")
                await get_state_manager().set_state(AssistantState.LISTENING)
                await get_event_bus().publish("assistant.response", {"text": "Yes? I'm listening!"}, source="voice_pipeline")
                try:
                    await get_tts_provider().speak("Yes? I'm listening!")
                except Exception:
                    pass
                return
            # Wake word + actual command text
            await self._on_command(command.strip())
        elif in_command_mode or in_conv_window:
            # Already in command-listening mode or inside open conversation window
            if transcript and transcript.strip():
                logger.info(f"Processing follow-up command (conv_window={in_conv_window}): '{transcript}'")
                await self._on_command(transcript.strip())
        else:
            # In passive WAKE_LISTENING mode with no wake word — ignore
            logger.debug(f"Passive listening: ignoring background speech (state={self._asm.state.value}): '{transcript[:50]}'")
            return

    async def _on_command(self, command: str) -> None:
        """Run the command through the shared runner (wake -> reason -> speak)."""
        self._asm.transition(AudioState.PROCESSING, "understanding command")
        await get_state_manager().set_state(AssistantState.UNDERSTANDING, {"text": command})
        try:
            await run_command(command)
        except Exception as e:
            logger.error(f"Command handling failed: {e}")
        finally:
            self._asm.transition(AudioState.WAKE_LISTENING, "return to wake-listening")

    async def _on_tts_cancel(self, event) -> None:
        """Barge-in: stop current TTS immediately (Section 16)."""
        logger.info("Barge-in: cancelling TTS")
        try:
            await get_tts_provider().cancel()
        except Exception as e:
            logger.warning(f"TTS cancel error: {e}")
        self._asm.transition(AudioState.INTERRUPTED, "barge-in")
        await get_state_manager().set_state(AssistantState.LISTENING)
        self._asm.transition(AudioState.COMMAND_LISTENING, "listening after interrupt")


_voice_pipeline = VoicePipeline()


def get_voice_pipeline() -> VoicePipeline:
    return _voice_pipeline
