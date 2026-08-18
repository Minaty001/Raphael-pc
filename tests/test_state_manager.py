import pytest
from raphael.core.state_manager import StateManager, AssistantState

@pytest.mark.anyio
async def test_state_manager_transitions():
    sm = StateManager()
    assert sm.current_state == AssistantState.OFFLINE

    await sm.set_state(AssistantState.IDLE)
    assert sm.current_state == AssistantState.IDLE

    await sm.set_state(AssistantState.LISTENING)
    assert sm.current_state == AssistantState.LISTENING

    await sm.set_state(AssistantState.THINKING)
    assert sm.current_state == AssistantState.THINKING
