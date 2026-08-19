"""
Unit tests for real LLM streaming (audit #19 / ROADMAP Phase 4).

Proves streaming is genuine (tokens yielded as the server sends them), NOT a
fake word-split replay of a fully buffered response.
"""

import sys
import os
import json
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from raphael.brain.llm_router import (
    OllamaProvider,
    GroqProvider,
    OpenAICompatibleProvider,
)


class FakeStreamingResp:
    """Mimics a streaming HTTP response: yields body lines one-at-a-time."""

    def __init__(self, lines):
        self._lines = [l if isinstance(l, bytes) else l.encode("utf-8") for l in lines]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self._lines)


def _patch_urlopen(monkeypatch, resp):
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: resp)


@pytest.mark.anyio
async def test_ollama_stream_is_real_not_buffered(monkeypatch):
    # NDJSON chunks the server would send incrementally.
    ndjson_lines = [
        json.dumps({"message": {"content": "Hello"}, "done": False}).encode(),
        json.dumps({"message": {"content": " world"}, "done": False}).encode(),
        json.dumps({"message": {"content": "!"}, "done": True}).encode(),
    ]
    resp = FakeStreamingResp(ndjson_lines)
    _patch_urlopen(monkeypatch, resp)

    prov = OllamaProvider(host="http://localhost:11434", model="llama3:8b")

    # Prove it does NOT go through chat() (which would buffer the full reply).
    async def boom(*a, **k):
        raise AssertionError("chat() must not be called by stream()")

    prov.chat = boom  # type: ignore

    chunks = [c async for c in prov.stream([{"role": "user", "content": "hi"}])]
    assert chunks == ["Hello", " world", "!"], chunks
    assert "".join(chunks) == "Hello world!"


@pytest.mark.anyio
async def test_groq_sse_stream_is_real(monkeypatch):
    sse_lines = [
        b'data: {"choices":[{"delta":{"content":"The"}}]}',
        b'data: {"choices":[{"delta":{"content":" answer"}}]}',
        b"data: [DONE]",
    ]
    resp = FakeStreamingResp(sse_lines)
    _patch_urlopen(monkeypatch, resp)

    prov = GroqProvider(api_key="x" * 20, model="llama-3.3-70b-versatile")

    async def boom(*a, **k):
        raise AssertionError("chat() must not be called by stream()")

    prov.chat = boom  # type: ignore

    chunks = [c async for c in prov.stream([{"role": "user", "content": "q"}])]
    assert chunks == ["The", " answer"], chunks
    assert "".join(chunks) == "The answer"


@pytest.mark.anyio
async def test_chat_equals_concatenated_stream(monkeypatch):
    ndjson_lines = [
        json.dumps({"message": {"content": "One"}, "done": False}).encode(),
        json.dumps({"message": {"content": " Two"}, "done": True}).encode(),
    ]
    resp = FakeStreamingResp(ndjson_lines)
    _patch_urlopen(monkeypatch, resp)

    prov = OllamaProvider(host="http://localhost:11434", model="llama3:8b")
    full = await prov.chat([{"role": "user", "content": "hi"}])
    assert full == "One Two"


@pytest.mark.anyio
async def test_local_mock_streams_without_sleep():
    from raphael.brain.llm_router import LocalMockProvider

    prov = LocalMockProvider()
    chunks = [c async for c in prov.stream([{"role": "user", "content": "hi"}])]
    assert len(chunks) > 1
    assert "".join(chunks).startswith("Raphael Assistant (Local Mode)")
