"""Truthfulness checks for the native voice health probe."""

import pytest

from raphael.runtime.health_monitor import RuntimeHealthMonitor


class _WakeDetector:
    enabled = True


class _Mic:
    def __init__(self, available, running=False):
        self.available = available
        self._running = running


@pytest.mark.anyio
async def test_voice_probe_reports_missing_microphone_backend(monkeypatch):
    import raphael.voice.microphone as microphone
    import raphael.voice.wakeword as wakeword

    monkeypatch.setattr(microphone, "get_microphone", lambda: _Mic(available=False))
    monkeypatch.setattr(wakeword, "get_wake_word_detector", lambda: _WakeDetector())

    monitor = RuntimeHealthMonitor()
    result = await monitor._probes["voice"]()

    assert result["status"] == "unavailable"
    assert "sounddevice" in result["detail"]


@pytest.mark.anyio
async def test_voice_probe_reports_stopped_capture(monkeypatch):
    import raphael.voice.microphone as microphone
    import raphael.voice.wakeword as wakeword

    monkeypatch.setattr(microphone, "get_microphone", lambda: _Mic(available=True, running=False))
    monkeypatch.setattr(wakeword, "get_wake_word_detector", lambda: _WakeDetector())

    monitor = RuntimeHealthMonitor()
    result = await monitor._probes["voice"]()

    assert result["status"] == "degraded"
    assert "not running" in result["detail"]
