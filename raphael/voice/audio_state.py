"""
Audio State Machine for Raphael v3 Always-Alive Runtime.
Implements the 9 audio states from the Always-Alive spec (Section 36).

States:
    AUDIO_IDLE          - Nothing happening, runtime idle.
    WAKE_LISTENING      - Low-power wake-word detection active (mic open, STT NOT running).
    WAKE_DETECTED       - Wake phrase matched in rolling buffer; bridging to command capture.
    COMMAND_LISTENING   - Full STT capturing the user's command.
    PROCESSING          - STT complete; command understood & being executed.
    SPEAKING            - TTS playback active.
    INTERRUPTED         - User barge-in; speech cancelled, returning to listening.
    PAUSED              - Voice paused by user (privacy), background work may continue.
    ERROR               - Audio subsystem fault; watchdog will attempt recovery.
"""

from enum import Enum
import time
from typing import Dict, Any, Optional
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger

logger = get_logger("voice.audio_state")


class AudioState(str, Enum):
    AUDIO_IDLE = "AUDIO_IDLE"
    WAKE_LISTENING = "WAKE_LISTENING"
    WAKE_DETECTED = "WAKE_DETECTED"
    COMMAND_LISTENING = "COMMAND_LISTENING"
    PROCESSING = "PROCESSING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class AudioStateMachine:
    """Single source of truth for the audio subsystem state."""

    def __init__(self):
        self._state = AudioState.AUDIO_IDLE
        self._prev = AudioState.AUDIO_IDLE
        self._transition_at = time.time()

    @property
    def state(self) -> AudioState:
        return self._state

    @property
    def state_value(self) -> str:
        return self._state.value

    def transition(self, new_state: AudioState, reason: str = "") -> None:
        if new_state == self._state:
            return
        self._prev = self._state
        self._state = new_state
        self._transition_at = time.time()
        logger.info(f"Audio state: {self._prev.value} -> {self._state.value} ({reason})")
        bus = get_event_bus()
        # Broadcast for the UI (Section 68 / 71) and for internal wiring.
        import asyncio
        try:
            asyncio.get_running_loop().create_task(
                bus.publish(
                    "audio.state",
                    {
                        "state": self._state.value,
                        "previous": self._prev.value,
                        "reason": reason,
                        "timestamp": self._transition_at,
                    },
                    source="audio_state",
                )
            )
        except RuntimeError:
            # No running loop (e.g. construction-time); fire-and-forget sync publish.
            pass

    def snapshot(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "previous": self._prev.value,
            "duration_seconds": round(time.time() - self._transition_at, 2),
        }


_audio_state_machine = AudioStateMachine()


def get_audio_state_machine() -> AudioStateMachine:
    return _audio_state_machine
