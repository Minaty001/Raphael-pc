"""
Unit tests for streaming STT (audit #4 remainder / ROADMAP L3.6).

Proves:
  * VoskProvider.transcribe_stream yields PARTIAL transcripts per chunk (real
    incremental streaming) and a FINAL transcript at the end -- NOT a single
    buffered result.
  * The base/Whisper default transcribe_stream is buffered (collects all chunks
    then emits only the final) -- honest for non-incremental engines.
"""

import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from raphael.voice.stt import VoskProvider, WhisperProvider, get_stt_provider


class FakeRecognizer:
    """Mimics a Vosk KaldiRecognizer returning per-chunk partials + a final."""

    def __init__(self, partials, final):
        self._partials = list(partials)
        self._final = final
        self._i = 0

    def AcceptWaveform(self, chunk):
        return True

    def PartialResult(self):
        # Return the next staged partial (or empty), simulating live decoding.
        if self._i < len(self._partials):
            p = self._partials[self._i]
            self._i += 1
            return json.dumps({"partial": p})
        return json.dumps({"partial": ""})

    def Result(self):
        return json.dumps({"text": self._final})


async def _chunk_gen(chunks):
    for c in chunks:
        yield c


@pytest.mark.anyio
async def test_vosk_stream_emits_partials_then_final(monkeypatch):
    prov = VoskProvider(model_path="/tmp/fake_vosk_model")
    # Force _ensure() to succeed with our fake recognizer (no real vosk needed).
    fake = FakeRecognizer(partials=["hey", "hey raphael", "hey raphael open"], final="hey raphael open chrome")
    monkeypatch.setattr(prov, "_ensure", lambda: True)
    monkeypatch.setattr(prov, "_recognizer", fake, raising=False)

    chunks = [b"\x00\x01", b"\x02\x03", b"\x04\x05"]
    out = [t async for t in prov.transcribe_stream(_chunk_gen(chunks))]

    # Partial transcripts must appear BEFORE the final, and there must be >1
    # yield (proving it is not a single buffered result).
    assert out == ["hey", "hey raphael", "hey raphael open", "hey raphael open chrome"], out
    assert len(out) > 1
    assert out[-1] == "hey raphael open chrome"


@pytest.mark.anyio
async def test_base_transcribe_stream_is_buffered(monkeypatch):
    # WhisperProvider has no native streaming -> uses buffered default.
    prov = WhisperProvider(model_size="base")
    calls = {"n": 0}

    async def fake_transcribe(audio_data):
        calls["n"] += 1
        return "final only"

    monkeypatch.setattr(prov, "transcribe", fake_transcribe)

    chunks = [b"a", b"b", b"c"]
    out = [t async for t in prov.transcribe_stream(_chunk_gen(chunks))]

    # Buffered: transcribe called ONCE with the joined audio, single final yield.
    assert calls["n"] == 1, f"expected buffered single call, got {calls['n']}"
    assert out == ["final only"], out


@pytest.mark.anyio
async def test_get_stt_provider_returns_instance():
    prov = get_stt_provider()
    assert prov is not None
    assert hasattr(prov, "transcribe")
    assert hasattr(prov, "transcribe_stream")
