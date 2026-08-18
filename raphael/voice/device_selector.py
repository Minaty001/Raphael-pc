"""
Audio Input Device Selector for Raphael v3 Always-Alive Runtime.

Implements intelligent auto-detection of the best microphone source:

  Priority cascade (highest → lowest):
    1. Bluetooth microphone  — if a BT audio device is actively connected
    2. USB microphone         — external USB mic/headset
    3. Built-in microphone    — system default (laptop internal mic, etc.)

  The selector re-evaluates on every call to `select_best_device()`, so it
  naturally adapts when a Bluetooth headset is paired/unpaired mid-session.

  A background monitor thread (`DeviceHotswapMonitor`) can optionally poll
  for device changes and invoke a callback (e.g. restart the capture stream)
  when the optimal device changes.

Usage:
    selector = get_device_selector()
    device = selector.select_best_device()
    # device.index  → sounddevice device index (or None for system default)
    # device.name   → human-readable label
    # device.rate   → native sample rate
    # device.kind   → 'bluetooth' | 'usb' | 'builtin' | 'unknown'
"""

import re
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Tuple

from raphael.core.logging import get_logger

logger = get_logger("voice.device_selector")


# ---------------------------------------------------------------------------
# Transport classification
# ---------------------------------------------------------------------------

class DeviceTransport(IntEnum):
    """Audio device transport type, ordered by selection priority (lower = higher priority)."""
    BLUETOOTH = 0
    USB = 1
    BUILTIN = 2
    VIRTUAL = 3   # PulseAudio/PipeWire monitor, loopback, etc.
    UNKNOWN = 4


# Regex patterns used to classify a device by its ALSA / PulseAudio name.
# These are matched case-insensitively against the device name string
# returned by `sounddevice.query_devices()`.
_BLUETOOTH_PATTERNS = re.compile(
    r"(bluetooth|bluez|bt[-_ ]?audio|bt[-_ ]?mic|airpods|galaxy buds|"
    r"jbl|sony wh|bose|beats|jabra|plantronics|sennheiser btd)",
    re.IGNORECASE,
)
_USB_PATTERNS = re.compile(
    r"(usb|yeti|snowball|scarlett|focusrite|rode|at2020|samson|"
    r"fifine|tonor|hyperx|blue mic|elgato wave)",
    re.IGNORECASE,
)
_VIRTUAL_PATTERNS = re.compile(
    r"(monitor|loopback|virtual|null|pipewire.*sink|pulse.*monitor)",
    re.IGNORECASE,
)


def classify_transport(device_name: str) -> DeviceTransport:
    """Determine the transport type of an audio device from its name string.

    Args:
        device_name: The human-readable device name from the audio subsystem.

    Returns:
        A DeviceTransport enum value indicating the detected transport.
    """
    if _BLUETOOTH_PATTERNS.search(device_name):
        return DeviceTransport.BLUETOOTH
    if _USB_PATTERNS.search(device_name):
        return DeviceTransport.USB
    if _VIRTUAL_PATTERNS.search(device_name):
        return DeviceTransport.VIRTUAL
    # Common built-in mic names on Linux ALSA
    if re.search(r"(analog|internal|built.?in|realtek|alc|hda|sof-|intelmicro)", device_name, re.IGNORECASE):
        return DeviceTransport.BUILTIN
    return DeviceTransport.UNKNOWN


# ---------------------------------------------------------------------------
# Device info container
# ---------------------------------------------------------------------------

@dataclass
class AudioInputDevice:
    """Snapshot of a detected audio input device."""
    index: Optional[int]           # sounddevice device index (None = system default)
    name: str                      # human-readable label
    kind: str                      # 'bluetooth' | 'usb' | 'builtin' | 'virtual' | 'unknown'
    transport: DeviceTransport     # numeric priority for sorting
    max_input_channels: int = 1    # number of input channels the device supports
    default_samplerate: float = 44100.0  # native sample rate reported by the driver
    is_default: bool = False       # True if this is the system default input device

    @property
    def rate(self) -> int:
        """Native sample rate as an integer."""
        return int(self.default_samplerate)

    def __repr__(self) -> str:
        default_tag = " [DEFAULT]" if self.is_default else ""
        return f"AudioInputDevice(#{self.index} '{self.name}' {self.kind}{default_tag} @ {self.rate}Hz)"


# ---------------------------------------------------------------------------
# Device selector
# ---------------------------------------------------------------------------

class DeviceSelector:
    """Enumerates audio input devices and selects the best one.

    Selection rules:
      1. Filter to input-capable devices only (max_input_channels > 0).
      2. Exclude virtual/monitor devices (loopbacks, PipeWire monitors).
      3. Sort by transport priority: Bluetooth > USB > Built-in > Unknown.
      4. Within the same transport tier, prefer the system default device.
      5. If no devices are found at all, return a fallback representing the
         system default (index=None), which lets sounddevice pick.

    The selector is stateless — each call to `select_best_device()` re-queries
    the audio subsystem, so Bluetooth connect/disconnect is picked up immediately.
    """

    def __init__(self):
        self._sd = None       # sounddevice module (lazy import)
        self._available = self._probe()

    # ------------------------------------------------------------------
    # Probe for the audio backend
    # ------------------------------------------------------------------
    def _probe(self) -> bool:
        """Try to import sounddevice. Returns False on headless systems."""
        try:
            import sounddevice as sd  # type: ignore
            self._sd = sd
            return True
        except Exception as e:
            logger.info(f"Device selector disabled (no sounddevice: {e})")
            return False

    @property
    def available(self) -> bool:
        """True if the audio subsystem is importable and usable."""
        return self._available

    # ------------------------------------------------------------------
    # Device enumeration
    # ------------------------------------------------------------------
    def enumerate_input_devices(self) -> List[AudioInputDevice]:
        """Return a list of all detected audio input devices.

        Each device is classified by transport type (Bluetooth, USB, built-in,
        virtual, unknown) and annotated with its native sample rate and channel
        count. Virtual/monitor devices are included in the list but excluded
        from automatic selection.
        """
        if not self._available:
            return []

        sd = self._sd
        try:
            all_devices = sd.query_devices()
        except Exception as e:
            logger.warning(f"Failed to query audio devices: {e}")
            return []

        # Identify the system default input device index
        try:
            default_input_idx = sd.default.device[0]  # (input_idx, output_idx)
        except Exception:
            default_input_idx = None

        results: List[AudioInputDevice] = []

        for idx, dev in enumerate(all_devices):
            # Skip output-only devices
            max_in = dev.get("max_input_channels", 0)
            if max_in <= 0:
                continue

            name = dev.get("name", f"Device {idx}")
            transport = classify_transport(name)

            results.append(AudioInputDevice(
                index=idx,
                name=name,
                kind=transport.name.lower(),
                transport=transport,
                max_input_channels=max_in,
                default_samplerate=dev.get("default_samplerate", 44100.0),
                is_default=(idx == default_input_idx),
            ))

        return results

    # ------------------------------------------------------------------
    # Selection logic
    # ------------------------------------------------------------------
    def select_best_device(self) -> AudioInputDevice:
        """Select the optimal microphone using the priority cascade.

        Priority:
          0. Manual override from config.voice.preferred_device (if set)
          1. Bluetooth mic (if connected and detected)
          2. USB mic
          3. Built-in / system default mic

        Returns:
            An AudioInputDevice describing the selected device. If no devices
            are detected, returns a fallback with index=None (system default).
        """
        devices = self.enumerate_input_devices()

        if not devices:
            logger.info("No input devices detected; using system default.")
            return self._system_default_fallback()

        # --- Priority 0: Manual override via config ---
        try:
            from raphael.core.configuration import get_config
            preferred = (get_config().voice.preferred_device or "").strip()
        except Exception:
            preferred = ""

        if preferred:
            matches = [d for d in devices if preferred.lower() in d.name.lower()]
            if matches:
                selected = matches[0]
                logger.info(f"Using preferred device override '{preferred}': {selected}")
                return selected
            logger.warning(
                f"Preferred device '{preferred}' not found among "
                f"{[d.name for d in devices]}; falling back to auto-detect."
            )

        # --- Priority 1-3: Auto-detect by transport ---
        # Filter out virtual/loopback devices from automatic selection
        candidates = [d for d in devices if d.transport != DeviceTransport.VIRTUAL]
        if not candidates:
            candidates = devices  # All virtual? Use whatever we have.

        # Sort by transport priority (Bluetooth=0, USB=1, Builtin=2, Unknown=4),
        # then prefer the system default within the same tier.
        candidates.sort(key=lambda d: (d.transport.value, not d.is_default))

        selected = candidates[0]
        logger.debug(
            f"Auto-selected microphone: {selected} "
            f"(from {len(devices)} input device(s), "
            f"{sum(1 for d in devices if d.transport == DeviceTransport.BLUETOOTH)} Bluetooth, "
            f"{sum(1 for d in devices if d.transport == DeviceTransport.USB)} USB, "
            f"{sum(1 for d in devices if d.transport == DeviceTransport.BUILTIN)} Built-in)"
        )
        return selected

    def _system_default_fallback(self) -> AudioInputDevice:
        """Construct a fallback device entry representing the system default.

        When index=None, sounddevice will use whatever the OS has configured
        as the default input device.
        """
        rate = 44100.0
        if self._available:
            try:
                info = self._sd.query_devices(kind="input")
                rate = info.get("default_samplerate", 44100.0)
            except Exception:
                pass

        return AudioInputDevice(
            index=None,
            name="System Default",
            kind="unknown",
            transport=DeviceTransport.UNKNOWN,
            default_samplerate=rate,
            is_default=True,
        )


# ---------------------------------------------------------------------------
# Hotswap monitor (optional background polling)
# ---------------------------------------------------------------------------

class DeviceHotswapMonitor:
    """Polls for audio device changes and triggers a callback on hotswap.

    This catches Bluetooth headset pair/unpair, USB mic plug/unplug, etc.
    The monitor compares the currently selected device against the previous
    selection on each tick. When the optimal device changes, it invokes the
    registered callback so the capture stream can be restarted on the new device.

    Usage:
        monitor = DeviceHotswapMonitor(selector, on_change=restart_capture)
        monitor.start()
        ...
        monitor.stop()
    """

    def __init__(
        self,
        selector: DeviceSelector,
        on_change: Optional[Callable[[AudioInputDevice, AudioInputDevice], None]] = None,
        poll_interval_seconds: float = 5.0,
    ):
        self._selector = selector
        self._on_change = on_change
        self._interval = poll_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_device: Optional[AudioInputDevice] = None

    def start(self) -> None:
        """Start the background polling thread."""
        if self._running or not self._selector.available:
            return
        self._running = True
        self._last_device = self._selector.select_best_device()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="raphael-device-monitor",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            f"Device hotswap monitor started (polling every {self._interval}s, "
            f"current device: {self._last_device})"
        )

    def stop(self) -> None:
        """Stop the background polling thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._interval + 1.0)
        self._thread = None
        logger.info("Device hotswap monitor stopped.")

    @property
    def current_device(self) -> Optional[AudioInputDevice]:
        """The most recently selected device (may be stale by up to poll_interval)."""
        return self._last_device

    def _poll_loop(self) -> None:
        """Background thread: periodically check if the best device has changed."""
        while self._running:
            time.sleep(self._interval)
            if not self._running:
                break

            try:
                new_device = self._selector.select_best_device()
            except Exception as e:
                logger.warning(f"Device poll failed: {e}")
                continue

            # Compare by device index and transport — name alone can be unstable
            if self._last_device is None or (
                new_device.index != self._last_device.index
                or new_device.transport != self._last_device.transport
            ):
                old = self._last_device
                self._last_device = new_device
                logger.info(
                    f"Audio device change detected: "
                    f"{old} → {new_device}"
                )
                if self._on_change:
                    try:
                        self._on_change(old, new_device)
                    except Exception as e:
                        logger.error(f"Device change callback failed: {e}")


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_device_selector = DeviceSelector()


def get_device_selector() -> DeviceSelector:
    """Return the global DeviceSelector instance."""
    return _device_selector
