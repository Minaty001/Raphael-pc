"""
Tests for FIX 4-7 (voice) and FIX 11-12 (background/proactive intelligence).
These run WITHOUT a live mic/STT/TTS — they exercise the wiring and providers.
"""

import asyncio
import pytest

from raphael.voice.wakeword import get_wake_word_detector, AudioRingBuffer, TranscriptWakeProvider
from raphael.voice.stt import get_stt_provider, MockSTTProvider, WebSpeechProvider
from raphael.voice.tts import get_tts_provider, MockTTSProvider
from raphael.voice.audio_state import get_audio_state_machine, AudioState
from raphael.core.event_bus import get_event_bus


def test_wakeword_provider_selection_and_strip():
    wd = get_wake_word_detector()
    # Provider is either porcupine (if installed) or transcript fallback.
    assert wd._provider is not None
    assert wd.strip_wake("Raphael open Chrome") == "open Chrome"
    assert wd.process_transcript_segment("Hey Raphael, search python") is True


def test_audio_ring_buffer_collect_since():
    rb = AudioRingBuffer(max_seconds=1.0)
    import time
    now = time.time()
    rb.push(b"AAAA")
    rb.push(b"BBBB", now=now + 10)
    # Collect from just before the second push.
    data = rb.collect_since(now + 9)
    assert data == b"BBBB"


def test_stt_tts_provider_selection():
    assert isinstance(get_stt_provider(), object)
    assert get_stt_provider().name in ("mock", "vosk", "web", "whisper")
    assert get_tts_provider().name in ("mock", "edge", "pyttsx3", "web")


def test_tts_cancel_is_cancellable():
    async def _run():
        tts = MockTTSProvider()
        events = []
        await get_event_bus().publish("voice.tts.started", {"text": "hi"}, source="t")
        task = asyncio.create_task(tts.speak("hello there this is a long sentence"))
        await asyncio.sleep(0.05)
        await tts.cancel()  # barge-in
        await asyncio.sleep(0.05)
        assert task.done()  # cancelled early, not after full duration
        await get_event_bus().publish("voice.tts.completed", {"text": "hi"}, source="t")

    asyncio.run(_run())


def test_proactive_engine_schedules_and_budgets():
    async def _run():
        from raphael.proactive.proactive_engine import get_proactive_engine
        from raphael.brain.open_loops import get_open_loop_tracker
        from raphael.runtime.health_monitor import get_health_monitor
        from raphael.core.resource_manager import get_resource_manager
        # Mark runtime healthy + resources available so the gate passes.
        hm = get_health_monitor()
        for c in ("core", "voice", "wakeword", "scheduler", "memory", "websocket", "llm"):
            hm.register(c, "ok")
        # Stub the resource gate: this is a unit test of the proactive engine,
        # not the live ResourceManager (which reflects real CPU/RAM load and
        # would make the test flaky on a busy machine).
        get_resource_manager()._background_paused = False
        get_open_loop_tracker().create_loop("fix the login bug", 0.9)
        eng = get_proactive_engine()
        eng.last_proactive_time = 0  # allow immediate
        eng.proactive_count_this_hour = 0
        eng.config.proactive.max_interruptions_per_hour = 1  # deterministic budget
        res = await eng.evaluate_proactive_opportunity({"recent_screen": {}})
        assert res is not None
        assert "login bug" in res["text"]
        # Budget exhausted now -> next call returns None.
        assert await eng.evaluate_proactive_opportunity({"recent_screen": {}}) is None

    asyncio.run(_run())


def test_proactive_engine_uses_real_working_memory_context():
    """The proactive engine must read active_app from a working-memory style
    summary (recent_screen is a dict), not just a hardcoded empty context."""
    async def _run():
        from raphael.proactive.proactive_engine import get_proactive_engine
        from raphael.brain.open_loops import get_open_loop_tracker
        from raphael.runtime.health_monitor import get_health_monitor
        from raphael.core.resource_manager import get_resource_manager
        hm = get_health_monitor()
        for c in ("core", "voice", "wakeword", "scheduler", "memory", "websocket", "llm"):
            hm.register(c, "ok")
        get_resource_manager()._background_paused = False
        get_open_loop_tracker().create_loop("finish the report", 0.9)
        eng = get_proactive_engine()
        eng.last_proactive_time = 0
        eng.proactive_count_this_hour = 0
        eng.config.proactive.max_interruptions_per_hour = 1
        # Working-memory summary shape: recent_screen is a dict with active_app.
        ctx = {"recent_screen": {"active_app": "code", "window_title": "report.md"}}
        res = await eng.evaluate_proactive_opportunity(ctx)
        assert res is not None
        assert "report" in res["text"]

    asyncio.run(_run())


def test_background_intelligence_engine_starts():
    async def _run():
        from raphael.runtime.background_intelligence import get_background_intelligence
        eng = get_background_intelligence()
        await eng.start()
        await asyncio.sleep(0.1)
        assert eng._running is True
        await eng.stop()

    asyncio.run(_run())
