"""
Shared voice command runner for Raphael Always-Alive Runtime.

Single source of truth for: wake-detected / typed command ->
  understand (reasoning engine) -> respond (TTS) -> return to wake-listening.

Used by both the VoicePipeline (FIX 4) and the AlwaysAliveController (Sections
11-14) so the wake->command->speak flow is identical regardless of entry point.
"""

import asyncio
from typing import Optional

from raphael.core.logging import get_logger
from raphael.voice.audio_state import AudioState, get_audio_state_machine
from raphael.voice.tts import get_tts_provider

logger = get_logger("voice.pipeline_helpers")


async def run_command(text: str) -> Optional[str]:
    """Process a user command: reason about it, speak the reply. Returns text."""
    if not text or not text.strip():
        return None
    from raphael.brain.reasoning import get_reasoning_engine

    asm = get_audio_state_machine()
    try:
        result = await get_reasoning_engine().process_user_input(text)
    except Exception as e:
        logger.error(f"Reasoning failed for '{text}': {e}")
        result = {"response": "Sorry, I had trouble processing that."}

    response = ""
    if isinstance(result, dict):
        response = result.get("response") or result.get("text") or ""
    elif isinstance(result, str):
        response = result

    if response:
        asm.transition(AudioState.SPEAKING, "responding")
        try:
            await get_tts_provider().speak(response)
        except Exception as e:
            logger.warning(f"TTS speak failed: {e}")
    return response
