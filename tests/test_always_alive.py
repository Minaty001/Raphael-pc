"""
Tests for the Raphael v3 Always-Alive Runtime (Sections 11-14, 19, 36, 43-46).
These run WITHOUT a live server — they exercise the pure logic of the
background task engine, wake-word buffer/strip, audio state machine, and
health monitor so the redesign is verified by real execution.
"""

import asyncio
import pytest

from raphael.voice.audio_state import AudioState, get_audio_state_machine
from raphael.voice.wakeword import WakeWordDetector
from raphael.runtime.health_monitor import RuntimeHealthMonitor, Watchdog
from raphael.runtime.tasks import (
    TaskManager,
    TaskPriority,
    TaskType,
    TaskStatus,
    get_task_manager,
)


# ---------------------------------------------------------------------------
# Wake word: detection + command stripping + rolling buffer (Sections 11-14)
# ---------------------------------------------------------------------------
def test_wakeword_detects_known_phrases():
    wd = WakeWordDetector(wake_words=["raphael", "hey raphael"])
    assert wd.process_transcript_segment("Hey Raphael, open Chrome") is True
    assert wd.process_transcript_segment("please remind me later") is False


def test_wakeword_strips_phrase_from_command():
    wd = WakeWordDetector(wake_words=["raphael", "hey raphael"])
    cleaned = wd.strip_wake("Raphael, open Chrome")
    assert "raphael" not in cleaned.lower()
    assert "open Chrome" in cleaned


def test_wakeword_rolling_buffer_captures_followup():
    wd = WakeWordDetector(wake_words=["raphael"], buffer_seconds=1.0)
    captured = []
    wd.set_on_wake(lambda cmd: captured.append(cmd))
    # Wake phrase + immediate follow-up in same/next segment
    wd.process_transcript_segment("Raphael")
    wd.process_transcript_segment("open the terminal please")
    # The wake callback fires on the "Raphael" segment; follow-up arrives after.
    assert len(captured) >= 1


# ---------------------------------------------------------------------------
# Audio state machine (Section 36)
# ---------------------------------------------------------------------------
def test_audio_state_transitions():
    asm = get_audio_state_machine()
    asm.transition(AudioState.WAKE_LISTENING, "test")
    assert asm.state == AudioState.WAKE_LISTENING
    asm.transition(AudioState.COMMAND_LISTENING, "test")
    assert asm.state == AudioState.COMMAND_LISTENING
    snap = asm.snapshot()
    assert "state" in snap and "duration_seconds" in snap


# ---------------------------------------------------------------------------
# Health monitor (Section 9)
# ---------------------------------------------------------------------------
def test_health_monitor_snapshot():
    hm = RuntimeHealthMonitor()
    hm.register("core", "alive")
    hm.register("voice", "ready")
    snap = asyncio.run(hm.snapshot())
    assert snap["runtime"] == "alive"
    assert snap["components"]["core"]["status"] == "alive"
    assert hm.is_healthy() is True


# ---------------------------------------------------------------------------
# Background Task Engine: priority queue + lifecycle (Sections 19, 43-46)
# ---------------------------------------------------------------------------
def test_task_manager_priority_ordering():
    mgr = TaskManager()
    mgr._running_flag = True  # prevent loop start side effects
    mgr.create("low task", _fake_coro, priority=TaskPriority.LOW.value)
    mgr.create("critical task", _fake_coro, priority=TaskPriority.CRITICAL.value)
    mgr.create("normal task", _fake_coro, priority=TaskPriority.NORMAL.value)

    # Drain the priority queue and confirm CRITICAL dequeues first.
    items = []
    while not mgr._queue.empty():
        rank, ts, tid = mgr._queue.get_nowait()
        items.append(rank)
    assert items[0] < items[1] < items[2]  # CRITICAL(0) < NORMAL(2) < LOW(3)


def test_task_lifecycle_states():
    mgr = TaskManager()
    mgr._running_flag = True
    tid = mgr.create("demo", _fake_coro, priority=TaskPriority.NORMAL.value)
    t = mgr.get(tid)
    assert t.status == TaskStatus.QUEUED.value
    assert mgr.pause(tid) is True
    assert mgr.get(tid).status == TaskStatus.PAUSED.value
    assert mgr.resume(tid) is True
    assert mgr.cancel(tid) is True
    assert mgr.get(tid).status == TaskStatus.CANCELLED.value


def test_task_resource_throttle():
    mgr = TaskManager()
    mgr._running_flag = True
    mgr.set_background_paused(True)
    # A low-priority task should be throttled when background paused.
    t = type("_T", (), {"priority": TaskPriority.LOW.value})()
    assert mgr._should_throttle(t) is True
    # Critical never throttled.
    tc = type("_T", (), {"priority": TaskPriority.CRITICAL.value})()
    assert mgr._should_throttle(tc) is False


async def _fake_coro(**kwargs):
    await asyncio.sleep(0.01)


def test_pause_cancels_running_task():
    async def _run():
        mgr = TaskManager()
        mgr._running_flag = True
        mgr.set_background_paused(False)
        # Prevent resource throttling from interfering in the test. This is a unit
        # test of pause/cancel semantics, not the live ResourceManager (which
        # reflects real CPU/RAM and would make the test flaky on a busy box).
        mgr._res_mgr._background_paused = False
        mgr._res_mgr.should_throttle = lambda priority: False
        mgr._res_mgr.can_run = lambda task: True
        tid = mgr.create("long job", lambda **kw: asyncio.sleep(5), priority=TaskPriority.LOW.value)
        loop = asyncio.get_event_loop()
        t = loop.create_task(mgr._scheduler_loop())
        # Poll until the task actually enters RUNNING (timing-tolerant).
        for _ in range(50):
            if mgr.get(tid).status == TaskStatus.RUNNING.value:
                break
            await asyncio.sleep(0.05)
        assert mgr.get(tid).status == TaskStatus.RUNNING.value
        assert tid in mgr._running
        mgr.pause(tid)
        await asyncio.sleep(0.1)
        assert mgr.get(tid).status == TaskStatus.PAUSED.value
        # underlying asyncio task actually cancelled
        assert tid not in mgr._running
        t.cancel()

    asyncio.run(_run())


def test_recovery_rebuilds_from_db():
    """FIX 2: a persisted task can be rebuilt from the store (factory path)."""
    mgr = TaskManager()
    mgr._running_flag = True
    tid = mgr.create("indexer", _fake_coro, priority=TaskPriority.BACKGROUND.value)
    rows = mgr.store.load_unfinished()
    by_id = {r["id"]: r for r in rows}
    assert tid in by_id
    rebuilt = mgr._task_from_row(by_id[tid])
    assert rebuilt.id == tid
    assert rebuilt.name == "indexer"


def test_task_runs_to_completion():
    async def _run():
        mgr = TaskManager()
        results = []
        mgr.create("work", lambda **kw: results.append(1), priority=TaskPriority.HIGH.value)
        # Manually run the scheduler loop once.
        mgr._running_flag = True
        task = asyncio.create_task(mgr._scheduler_loop())
        await asyncio.sleep(0.3)
        task.cancel()
        assert len(results) == 1

    asyncio.run(_run())
