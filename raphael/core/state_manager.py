"""
Raphael State Manager.
Tracks and broadcasts the official 15 Raphael v3 Brain States over the Event Bus.
"""

from enum import Enum
import time
from typing import Dict, Any, Optional
from raphael.core.event_bus import get_event_bus
from raphael.core.logging import get_logger

logger = get_logger("core.state")

class AssistantState(str, Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    LISTENING = "LISTENING"
    UNDERSTANDING = "UNDERSTANDING"
    RETRIEVING_MEMORY = "RETRIEVING_MEMORY"
    THINKING = "THINKING"
    PLANNING = "PLANNING"
    ASKING = "ASKING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    LEARNING = "LEARNING"
    REFLECTING = "REFLECTING"
    SPEAKING = "SPEAKING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"

class StateManager:
    def __init__(self):
        self._current_state: AssistantState = AssistantState.OFFLINE
        self._previous_state: AssistantState = AssistantState.OFFLINE
        self._state_data: Dict[str, Any] = {}
        self._last_transition_time: float = time.time()

    @property
    def current_state(self) -> AssistantState:
        return self._current_state

    @property
    def state_duration(self) -> float:
        return time.time() - self._last_transition_time

    async def set_state(self, state: AssistantState, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Transitions the assistant to a new state and publishes an event.
        """
        if self._current_state == state and not data:
            return

        self._previous_state = self._current_state
        self._current_state = state
        self._state_data = data or {}
        self._last_transition_time = time.time()

        logger.info(f"State transition: {self._previous_state.value} -> {self._current_state.value}")

        event_bus = get_event_bus()
        await event_bus.publish({
            "type": "assistant.state",
            "state": self._current_state.value,
            "previous_state": self._previous_state.value,
            "data": self._state_data,
            "timestamp": self._last_transition_time
        })

    def get_summary(self) -> Dict[str, Any]:
        return {
            "current_state": self._current_state.value,
            "previous_state": self._previous_state.value,
            "duration_seconds": round(self.state_duration, 2),
            "state_data": self._state_data
        }

_state_manager = StateManager()

def get_state_manager() -> StateManager:
    return _state_manager
