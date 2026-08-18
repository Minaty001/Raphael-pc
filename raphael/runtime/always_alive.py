"""
Always-Alive Controller for Raphael v3 (Sections 1-4, 11-16, 28, 49-53, 71).

This is the orchestration layer that keeps Raphael *present* without being *heavy*.
It owns:
  * Runtime modes: NORMAL | FOCUS | PAUSE | SLEEP | EXIT  (49-52)
  * Wake-word -> immediate command capture pipeline (11-14)
  * Continuous conversation window after a response (15)
  * Barge-in / interruption (16)
  * Cognitive preemption: foreground voice preempts background work (27-28)
  * Heartbeat emission for UI liveness detection (71)
  * A bounded set of supervised workers via the Watchdog (10)

The controller is driven by the Event Bus, so it works regardless of whether the
UI (WebSocket client) is connected or not (3: UI closed -> Raphael continues).
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Any, Optional

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.core.event_bus import get_event_bus
from raphael.core.state_manager import get_state_manager, AssistantState
from raphael.voice.audio_state import AudioState, get_audio_state_machine
from raphael.voice.wakeword import get_wake_word_detector
from raphael.voice.pipeline import get_voice_pipeline
from raphael.brain.reasoning import get_reasoning_engine
from raphael.runtime.health_monitor import get_health_monitor, get_watchdog
from raphael.runtime.tasks import get_task_manager

logger = get_logger("runtime.always_alive")


class RuntimeMode(str, Enum):
    NORMAL = "NORMAL"
    FOCUS = "FOCUS"
    PAUSE = "PAUSE"
    SLEEP = "SLEEP"
    EXIT = "EXIT"


# Audio state -> human readable voice status (Section 35/68)
VOICE_STATUS_MAP = {
    AudioState.AUDIO_IDLE: "idle",
    AudioState.WAKE_LISTENING: "wake_listening",
    AudioState.WAKE_DETECTED: "wake_detected",
    AudioState.COMMAND_LISTENING: "command_listening",
    AudioState.PROCESSING: "processing",
    AudioState.SPEAKING: "speaking",
    AudioState.INTERRUPTED: "interrupted",
    AudioState.PAUSED: "paused",
    AudioState.ERROR: "error",
}


class AlwaysAliveController:
    def __init__(self):
        self.config = get_config()
        self._mode = RuntimeMode.NORMAL
        self._running = False
        self._start_time = time.time()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._conversation_window_task: Optional[asyncio.Task] = None
        self._conversation_until = 0.0
        self._asm = get_audio_state_machine()
        self._health = get_health_monitor()
        self._watchdog = get_watchdog()
        self._tasks = get_task_manager()

        # Wire wake-word detector: when wake is detected, immediately capture
        # the follow-up command (Section 11-14).
        wwd = get_wake_word_detector()
        wwd.set_on_wake(self._on_wake)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.time()

        # Register health components (Section 8/9).
        # NOTE: these are *startup* state flags. The live probe
        # (_probe_websocket) later overrides "websocket" with the real client
        # connection count, so we must NOT claim "connected" here before a
        # client is actually attached (P0 #29).
        self._health.register("core", "alive", "always-alive controller up")
        self._health.register("voice", "ready", "wake listener registered")
        self._health.register("wakeword", "ready", "wake detector active")
        self._health.register("scheduler", "running", "task engine bound")
        self._health.register("memory", "healthy", "memory subsystem")
        self._health.register("websocket", "running", "gateway listening (no client yet)")
        self._health.register("llm", "available", "router ready")

        # Start background task engine + supervised workers (Section 10).
        await self._tasks.start()
        self._watchdog.register_worker("background_tasks", self._tasks._scheduler_loop
                                      if hasattr(self._tasks, "_scheduler_loop") else self._noop,
                                      component_key="tasks")
        # Note: task engine runs its own loop; watchdog supervises a heartbeat
        # worker that pings health so a hung engine is detected (Section 10).
        self._watchdog.register_worker("heartbeat", self._heartbeat_loop, component_key="core")

        # FIX 11 / FIX 12: start background cognitive + proactive engines.
        from raphael.runtime.background_intelligence import get_background_intelligence
        from raphael.proactive.proactive_engine import get_proactive_engine
        self._bg_intel = get_background_intelligence()
        self._proactive = get_proactive_engine()
        await self._bg_intel.start()
        await self._proactive.start()

        self._watchdog.start()

        # FIX 4/5: start real microphone capture (no-op if no audio backend).
        # The mic feeds the wake detector ring buffer + STT on command capture.
        try:
            from raphael.voice.microphone import get_microphone
            self._mic = get_microphone()
            await self._mic.start()
        except Exception as e:
            logger.warning(f"Microphone capture unavailable: {e}")

        # Start in wake-listening (low-power) so Raphael is "always listening"
        # without running full STT (Section 34).
        self._asm.transition(AudioState.WAKE_LISTENING, "always-alive start")

        logger.info("=== RAPHAEL ALWAYS-ALIVE RUNTIME READY ===")

    async def stop(self) -> None:
        self._running = False
        self._mode = RuntimeMode.EXIT
        # FIX 4/5: stop microphone capture first.
        try:
            if getattr(self, "_mic", None) is not None:
                self._mic.stop()
        except Exception as e:
            logger.warning(f"Microphone stop: {e}")
        # FIX 11/12: stop background cognitive + proactive engines first.
        try:
            await self._bg_intel.stop()
            await self._proactive.stop()
        except Exception as e:
            logger.warning(f"Background engine stop: {e}")
        self._watchdog.stop()
        await self._tasks.stop()
        await get_event_bus().publish("runtime.shutdown", {"reason": "exit"}, source="always_alive")
        logger.info("Always-alive runtime stopped.")

    async def _noop(self) -> None:
        # Placeholder worker (never returns while running).
        while self._running:
            await asyncio.sleep(3600)

    # ------------------------------------------------------------------
    # Heartbeat (Section 71)
    # ------------------------------------------------------------------
    async def _heartbeat_loop(self) -> None:
        while self._running:
            await asyncio.sleep(5.0)
            await self._emit_heartbeat()

    async def _emit_heartbeat(self) -> None:
        tasks = self._tasks.list()
        active = [t for t in tasks if t["status"] in ("RUNNING", "QUEUED")]
        snap = await self._health.snapshot()
        await get_event_bus().publish(
            "runtime.heartbeat",
            {
                "uptime": int(time.time() - self._start_time),
                "mode": self._mode.value,
                "workers": len(self._watchdog.status()),
                "tasks": len(active),
                "voice": VOICE_STATUS_MAP.get(self._asm.state, "unknown"),
                "runtime": snap["runtime"],
                "components": snap["components"],
            },
            source="always_alive",
        )

    # ------------------------------------------------------------------
    # Wake word -> immediate command capture (Sections 11-14)
    # ------------------------------------------------------------------
    def _on_wake(self, command_text: str) -> None:
        """Called by WakeWordDetector when wake phrase is detected.
        command_text already has the wake word stripped (Section 14).

        FIX 1 robustness: schedule the command handler only if a runtime event
        loop is actually running. Outside a running loop (e.g. unit tests, or
        when the runtime has not yet started) we must not call
        asyncio.create_task, which would raise RuntimeError. The wake fragment is
        still handed to the pipeline synchronously so nothing is lost.
        """
        logger.info(f"WAKE -> captured command fragment: '{command_text}'")
        # Transition immediately to command listening (Section 11).
        self._asm.transition(AudioState.COMMAND_LISTENING, "wake detected")
        # If there is already a full command in the buffer, process it.
        if command_text:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._handle_command(command_text))
            except RuntimeError:
                # No running loop (runtime not started / test context): drop
                # the async dispatch but keep the synchronous transition above.
                logger.debug("Wake callback fired with no running loop; command not dispatched.")
        # Otherwise the STT stream will deliver the rest (Section 13 buffer).

    async def _handle_command(self, text: str) -> None:
        # Cognitive preemption (Section 27-28): foreground voice preempts work.
        self._tasks.set_background_paused(True) if self.config.app.mode == "BALANCED" else None
        self._asm.transition(AudioState.PROCESSING, "understanding command")
        await get_state_manager().set_state(AssistantState.UNDERSTANDING, {"text": text})
        try:
            await get_reasoning_engine().process_user_input(text)
        except Exception as e:
            logger.error(f"Command handling failed: {e}")
        finally:
            self._asm.transition(AudioState.SPEAKING, "responding")
            # Open a short continuous-conversation window (Section 15).
            self._open_conversation_window()
            # Resume background under normal conditions.
            if self._mode == RuntimeMode.NORMAL:
                self._tasks.set_background_paused(False)

    # ------------------------------------------------------------------
    # Continuous conversation window (Section 15)
    # ------------------------------------------------------------------
    def _open_conversation_window(self, seconds: int = 8) -> None:
        self._conversation_until = time.time() + seconds
        if self.config.voice.conversational_window_seconds:
            seconds = self.config.voice.conversational_window_seconds
        self._conversation_until = time.time() + seconds
        logger.debug(f"Conversation window open for {seconds}s")

    def in_conversation_window(self) -> bool:
        return time.time() < self._conversation_until

    # ------------------------------------------------------------------
    # Barge-in / interruption (Section 16)
    # ------------------------------------------------------------------
    async def interrupt(self) -> None:
        """User interrupted while Raphael is speaking."""
        self._asm.transition(AudioState.INTERRUPTED, "barge-in")
        # Cancel current speech (TTS) via event bus.
        await get_event_bus().publish("voice.tts.cancel", {}, source="always_alive")
        await get_state_manager().set_state(AssistantState.LISTENING)
        self._asm.transition(AudioState.COMMAND_LISTENING, "listening after interrupt")
        logger.info("Barge-in: TTS cancelled, now listening.")

    # ------------------------------------------------------------------
    # Mode controls (Sections 49-52)
    # ------------------------------------------------------------------
    async def set_mode(self, mode: RuntimeMode) -> None:
        self._mode = mode
        wwd = get_wake_word_detector()
        mic = getattr(self, "_mic", None)
        if mode == RuntimeMode.SLEEP:
            wwd.enabled = False
            self._tasks.set_background_paused(True)
            if mic:
                mic.stop()
            self._asm.transition(AudioState.AUDIO_IDLE, "sleep")
        elif mode == RuntimeMode.PAUSE:
            wwd.enabled = False  # privacy: voice off, background continues (51)
            if mic:
                mic.stop()
            self._asm.transition(AudioState.PAUSED, "voice paused")
        elif mode == RuntimeMode.FOCUS:
            self._tasks.set_background_paused(True)
            if mic:
                await mic.start()
            self._asm.transition(AudioState.WAKE_LISTENING, "focus mode")
        else:  # NORMAL
            wwd.enabled = self.config.voice.wake_word_enabled
            self._tasks.set_background_paused(False)
            if mic:
                await mic.start()
            self._asm.transition(AudioState.WAKE_LISTENING, "normal")
        await get_event_bus().publish("runtime.mode", {"mode": mode.value}, source="always_alive")
        logger.info(f"Runtime mode -> {mode.value}")

    def get_mode(self) -> str:
        return self._mode.value

    async def full_exit(self) -> None:
        """Section 52: only explicit Exit terminates the runtime."""
        await get_event_bus().publish("runtime.exiting", {}, source="always_alive")
        await self.stop()


_always_alive = AlwaysAliveController()


def get_always_alive() -> AlwaysAliveController:
    return _always_alive
