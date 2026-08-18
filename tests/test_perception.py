import pytest
from raphael.perception.screen_understanding import get_screen_observer

def test_structural_screen_state():
    observer = get_screen_observer()
    state = observer.get_structural_state()

    assert "active_app" in state
    assert "window_title" in state
    assert "detected_activity" in state
    assert "timestamp" in state

def test_screen_explanation():
    observer = get_screen_observer()
    explanation = observer.explain_current_screen("What am I looking at?")
    assert isinstance(explanation, str)
    assert len(explanation) > 10
