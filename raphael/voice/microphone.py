"""
Microphone capture source for Raphael v3 Always-Alive Runtime (FIX 4 / FIX 5).

FEEDS the voice pipeline with REAL audio:
  * Raw PCM is pushed to the WakeWordDetector ring buffer (FIX 5) so the
    words right after "Raphael" are never lost.
  * When the runtime is in COMMAND_LISTENING (Section 11/13/14) the captured
    audio is handed to the configured STT provider (FIX 6).

Auto-Device Selection:
  Uses DeviceSelector to automatically pick the best microphone:
    1. Bluetooth mic  — when a BT headset is actively paired
    2. USB mic         — external USB microphone
    3. Built-in mic    — system default (laptop internal)
  A DeviceHotswapMonitor polls for device changes every 5 seconds and
  automatically restarts the capture stream on the new device.

The capture source is OPTIONAL and defensive: it uses `sounddevice` when
available and silently disables itself otherwise (e.g. a headless server or a
machine without audio libs). This keeps the always-alive runtime alive and
functional even where no microphone is present — the WebSocket/browser path
(Web Speech) still works regardless.
"""

import asyncio
import threading
import time
from typing import Optional

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger
from raphael.voice.audio_state import get_audio_state_machine, AudioState
from raphael.voice.device_selector import (
    AudioInputDevice,
    DeviceHotswapMonitor,
    get_device_selector,
)


# Target rate for all downstream consumers (KWS / VAD / STT). Hardware may
# capture at a different native rate (e.g. 44100Hz); we always normalize.
TARGET_RATE = 16000


class Resampler:
    """Linear-interpolation resampler for mono 16-bit PCM.

    Normalizes arbitrary hardware sample rates down to TARGET_RATE (16kHz) so
    Porcupine / Vosk / VAD see a consistent stream regardless of what the
    microphone device natively reports (many mics default to 44100Hz).
    Stateful across chunks so boundaries don't cause clicks/pops.
    """

    def __init__(self, in_rate: int, out_rate: int = TARGET_RATE):
        self.in_rate = in_rate
        self.out_rate = out_rate
        self._last_in = 0.0
        self._pos = 0.0

    def resample(self, pcm: bytes) -> bytes:
        if self.in_rate == self.out_rate:
            return pcm
        import struct
        in_samples = struct.unpack("<%dh" % (len(pcm) // 2), pcm)
        if not in_samples:
            return b""
        ratio = self.out_rate / self.in_rate
        out = []
        pos = self._pos
        prev = self._last_in
        while True:
            i = int(pos)
            if i >= len(in_samples):
                break
            cur = in_samples[i]
            frac = pos - i
            val = prev + (cur - prev) * frac
            out.append(int(round(val)))
            prev = cur
            pos += 1.0 / ratio
        self._pos = pos - len(in_samples)
        self._last_in = in_samples[-1]
        return struct.pack("<%dh" % len(out), *out)


logger = get_logger("voice.microphone")


class MicrophoneSource:
    """Chooses a capture backend and streams PCM frames to the wake detector.

    On construction, queries the DeviceSelector for the best available input
    device (Bluetooth → USB → Built-in) and opens a RawInputStream on it.
    A background DeviceHotswapMonitor watches for device changes (e.g. BT
    headset paired/unpaired) and automatically restarts the capture stream.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1, block_ms: int = 30):
        cfg = get_config()
        self.sample_rate = cfg.voice.sample_rate or sample_rate
        self.channels = channels
        self.block_ms = block_ms
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sd = None
        self._available = self._probe()
        self._asm = get_audio_state_machine()

        # Capture the main asyncio event loop at construction time so the
        # sounddevice callback (which runs on a worker thread) can dispatch to
        # it safely via call_soon_threadsafe. The callback thread has NO
        # asyncio context, so it cannot call asyncio.get_event_loop() itself
        # (would raise RuntimeError), nor assume any loop is running.
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = None

        # Device auto-selection state
        self._selector = get_device_selector()
        self._current_device: Optional[AudioInputDevice] = None
        self._hotswap_monitor: Optional[DeviceHotswapMonitor] = None

    # ------------------------------------------------------------------
    def _probe(self) -> bool:
        """Return True if a capture backend is importable."""
        try:
            import sounddevice as sd  # type: ignore
            self._sd = sd
            return True
        except Exception as e:
            logger.info(f"Microphone capture disabled (no audio backend: {e})")
            return False

    @property
    def available(self) -> bool:
        return self._available

    @property
    def current_device(self) -> Optional[AudioInputDevice]:
        """The currently active audio input device, or None if not capturing."""
        return self._current_device

    # ------------------------------------------------------------------
    async def start(self) -> None:
        if not self._available or self._running:
            return

        # Select the best input device before starting capture
        self._current_device = self._selector.select_best_device()
        logger.info(f"Selected input device: {self._current_device}")

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, name="raphael-mic", daemon=True)
        self._thread.start()
        logger.info("Microphone capture started (real audio -> wake detector).")

        # Start hotswap monitoring — restarts capture when the best device changes
        self._start_hotswap_monitor()

    def stop(self) -> None:
        self._running = False
        # Stop hotswap monitor first
        if self._hotswap_monitor:
            self._hotswap_monitor.stop()
            self._hotswap_monitor = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._current_device = None
        logger.info("Microphone capture stopped.")

    # ------------------------------------------------------------------
    # Device hotswap
    # ------------------------------------------------------------------
    def _start_hotswap_monitor(self) -> None:
        """Start background polling for audio device changes."""
        self._hotswap_monitor = DeviceHotswapMonitor(
            selector=self._selector,
            on_change=self._on_device_change,
            poll_interval_seconds=5.0,
        )
        self._hotswap_monitor.start()

    def _on_device_change(
        self,
        old_device: Optional[AudioInputDevice],
        new_device: AudioInputDevice,
    ) -> None:
        """Callback from DeviceHotswapMonitor when the optimal mic changes.

        Stops the current capture thread and restarts it on the new device.
        This handles BT connect/disconnect, USB plug/unplug, etc.
        """
        logger.info(
            f"Hotswap: switching microphone from "
            f"'{old_device.name if old_device else 'None'}' "
            f"to '{new_device.name}'"
        )
        # Update the target device
        self._current_device = new_device

        # Restart the capture thread (stop current, start new)
        was_running = self._running
        if was_running:
            self._running = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            self._running = True
            self._thread = threading.Thread(
                target=self._capture_loop, name="raphael-mic", daemon=True
            )
            self._thread.start()
            logger.info(f"Capture restarted on new device: {new_device}")

    # ------------------------------------------------------------------
    # Capture loop
    # ------------------------------------------------------------------
    def _resolve_stream_params(self) -> dict:
        """Build the keyword arguments for `sd.RawInputStream`.

        Determines the device index and sample rate to use, falling back
        through multiple strategies if the preferred rate is unsupported.
        """
        sd = self._sd
        device = self._current_device
        device_index = device.index if device else None
        target_rate = self.sample_rate

        # Strategy 1: Use native sample rate if device provides one (avoids ALSA PaErrorCode -9997 noise)
        native_rate = device.rate if (device and device.rate) else 44100
        try:
            block = int(native_rate * self.block_ms / 1000)
            params = dict(
                device=device_index,
                samplerate=native_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=block,
            )
            test = sd.RawInputStream(**params, callback=lambda *_: None)
            test.close()
            return params
        except Exception:
            pass

        # Strategy 2: Try requested sample rate (e.g. 16000Hz)
        try:
            block = int(target_rate * self.block_ms / 1000)
            params = dict(
                device=device_index,
                samplerate=target_rate,
                channels=self.channels,
                dtype="int16",
                blocksize=block,
            )
            test = sd.RawInputStream(**params, callback=lambda *_: None)
            test.close()
            return params
        except Exception:
            pass
        try:
            info = sd.query_devices(device_index or sd.default.device[0])
            native_rate = int(info.get("default_samplerate", native_rate))
        except Exception:
            pass

        block = int(native_rate * self.block_ms / 1000)
        return dict(
            device=device_index,
            samplerate=native_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=block,
        )

    def _capture_loop(self) -> None:
        """Pull PCM frames on a worker thread; dispatch to wake/STT on the loop."""
        try:
            sd = self._sd
            loop = self._loop

            def _callback(indata, frames, time_info, status):
                if not self._running:
                    return
                pcm = bytes(indata)
                # Dispatch to the main asyncio loop. The callback runs on a
                # sounddevice worker thread with no asyncio context, so we must
                # use the loop captured at construction time + call_soon_threadsafe.
                if loop is not None and loop.is_running():
                    loop.call_soon_threadsafe(self._dispatch, pcm)
                else:
                    # Fallback: loop not available (e.g. headless/import-time) —
                    # skip dispatch rather than crash the capture thread.
                    pass

            # Resolve device + sample rate with automatic fallback
            stream_params = self._resolve_stream_params()
            device_name = self._current_device.name if self._current_device else "system default"
            effective_rate = int(stream_params.get("samplerate", self.sample_rate))
            # Build a resampler so downstream consumers (KWS/VAD/STT) always get
            # TARGET_RATE (16kHz) mono PCM, even if the device captures at a
            # different native rate (e.g. 44100Hz). P0: sample-rate bug.
            self._resampler = Resampler(in_rate=effective_rate, out_rate=TARGET_RATE)
            logger.info(
                f"Opening audio stream on '{device_name}' "
                f"(device={stream_params.get('device')}, rate={effective_rate}Hz -> {TARGET_RATE}Hz)"
            )

            stream = sd.RawInputStream(**stream_params, callback=_callback)

            with stream:
                while self._running:
                    time.sleep(0.05)
        except Exception as e:
            logger.warning(f"Microphone capture loop error: {e}")
            self._running = False

    def _dispatch(self, pcm: bytes) -> None:
        """Route a captured PCM frame to the right consumer (FIX 4/5/6).

        The raw chunk is normalized to 16kHz mono via the stream's resampler
        before being handed to KWS / VAD / STT so all consumers agree on the
        sample rate.
        """
        from raphael.voice.wakeword import get_wake_word_detector
        from raphael.voice.stt import get_stt_provider

        # Normalize sample rate -> TARGET_RATE for all downstream consumers.
        resampler = getattr(self, "_resampler", None)
        if resampler is not None:
            pcm = resampler.resample(pcm)

        wwd = get_wake_word_detector()
        # Always feed the ring buffer / KWS so a wake is detected (FIX 5).
        wwd.ingest_audio(pcm)

        # If we are actively capturing a command, run STT on this frame (FIX 6).
        if self._asm.state == AudioState.COMMAND_LISTENING:
            asyncio.ensure_future(self._transcribe(pcm, get_stt_provider()))

    async def _transcribe(self, pcm: bytes, stt) -> None:
        try:
            text = await stt.transcribe(pcm)
            if text and text.strip():
                from raphael.voice.pipeline import get_voice_pipeline
                await get_voice_pipeline().handle_speech_input(text, is_final=True)
        except Exception as e:
            logger.warning(f"Mic STT error: {e}")


_mic_source = MicrophoneSource()


def get_microphone() -> MicrophoneSource:
    return _mic_source
