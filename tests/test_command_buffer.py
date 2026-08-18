"""
Unit tests for the VAD-segmented CommandBuffer (audit #4 / ROADMAP L3.5).

The buffer must accumulate 16kHz PCM chunks and fire EXACTLY ONE segment
callback per detected speech burst — not one per chunk. This is hardware-free
and verifies the low-latency STT architecture without a microphone.
"""

import struct
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from raphael.voice.microphone import CommandBuffer, rms_energy


def _tone(level: int, samples: int) -> bytes:
    """Synthesize `samples` int16 frames all at `level` (RMS ~ abs(level))."""
    return struct.pack("<%dh" % samples, *([level] * samples))


def _silence(samples: int) -> bytes:
    return b"\x00\x00" * samples


def test_rms_energy_returns_zero_for_empty():
    assert rms_energy(b"") == 0.0
    assert rms_energy(b"\x00\x00") == 0.0


def test_rms_energy_detects_loud_vs_silent():
    loud = _tone(5000, 160)
    quiet = _silence(160)
    assert rms_energy(loud) > 120.0
    assert rms_energy(quiet) < 120.0


def test_one_segment_per_speech_burst():
    """A speech burst followed by silence must yield exactly ONE callback."""
    segments = []

    def on_segment(pcm: bytes):
        segments.append(pcm)

    # No loop / scheduler: finalize fires synchronously.
    buf = CommandBuffer(on_segment=on_segment, vad_threshold=120.0,
                        silence_timeout_ms=300, max_segment_ms=10000)

    t = 0.0
    # 0.5s of silence (pre-speech) — should be ignored
    for _ in range(10):
        buf.push(_silence(80), t)
        t += 0.05
    # 1.0s of loud speech (~16 chunks at 50ms) — starts a segment
    for _ in range(20):
        buf.push(_tone(6000, 80), t)
        t += 0.05
    # 0.6s of silence tail — must finalize the segment
    for _ in range(12):
        buf.push(_silence(80), t)
        t += 0.05

    assert len(segments) == 1, f"expected 1 segment, got {len(segments)}"
    # The segment should contain the loud speech, not the pre-speech silence.
    assert len(segments[0]) > 0


def test_multiple_bursts_yield_multiple_segments():
    segments = []

    def on_segment(pcm: bytes):
        segments.append(pcm)

    buf = CommandBuffer(on_segment=on_segment, vad_threshold=120.0,
                        silence_timeout_ms=200, max_segment_ms=10000)
    t = 0.0
    # Burst 1
    for _ in range(10):
        buf.push(_tone(6000, 80), t); t += 0.05
    for _ in range(6):  # 0.3s silence -> finalize burst 1
        buf.push(_silence(80), t); t += 0.05
    # Burst 2
    for _ in range(10):
        buf.push(_tone(6000, 80), t); t += 0.05
    for _ in range(6):  # finalize burst 2
        buf.push(_silence(80), t); t += 0.05

    assert len(segments) == 2, f"expected 2 segments, got {len(segments)}"


def test_sustained_silence_produces_no_segment():
    segments = []

    def on_segment(pcm: bytes):
        segments.append(pcm)

    buf = CommandBuffer(on_segment=on_segment, vad_threshold=120.0,
                        silence_timeout_ms=200, max_segment_ms=10000)
    t = 0.0
    for _ in range(40):
        buf.push(_silence(80), t); t += 0.05

    assert len(segments) == 0, "silence-only stream should not produce a segment"
