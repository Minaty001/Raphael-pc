"""
LLM Router and Unified Provider Interface for Raphael AI Assistant.
Supports Ollama, OpenRouter, Groq, OpenAI-compatible APIs, and local mock fallbacks.

Streaming is REAL (audit #19): each provider performs a genuine chunked HTTP
request (Ollama NDJSON, OpenAI-compatible SSE) and yields text deltas as they
arrive from the model server. ``chat()`` is derived from ``stream()`` so there
is a single network path and no fake word-split replay.
"""

import asyncio
import json
import threading
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncGenerator, Optional, Tuple, Callable

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("brain.llm_router")


async def _streaming_request(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    parse_fn: Callable[[bytes], List[str]],
    timeout: float = 60.0,
) -> AsyncGenerator[str, None]:
    """Perform a streaming HTTP POST and yield parsed text deltas as they arrive.

    A background thread reads the response line-by-line (NDJSON / SSE) and pushes
    parsed deltas into a queue; the async generator pulls from the queue so the
    event loop is never blocked waiting on the network.
    """
    # Use the event loop's queue and schedule puts thread-safely.  Calling a
    # blocking ``queue.Queue.get`` through ``asyncio.to_thread`` can leave the
    # stream suspended indefinitely during AnyIO/asyncio teardown, even after
    # the HTTP reader has delivered its final sentinel.
    loop = asyncio.get_running_loop()
    q: "asyncio.Queue[Any]" = asyncio.Queue()
    _SENTINEL = object()

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    def _worker() -> None:
        def _put(item: Any) -> None:
            loop.call_soon_threadsafe(q.put_nowait, item)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                for raw_line in resp:
                    for delta in parse_fn(raw_line):
                        if delta:
                            _put(delta)
        except Exception as exc:  # surface network/parse errors to the consumer
            _put(exc)
        finally:
            _put(_SENTINEL)

    threading.Thread(target=_worker, daemon=True).start()

    while True:
        item = await q.get()
        if item is _SENTINEL:
            break
        if isinstance(item, Exception):
            raise item
        yield item


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        pass

    @abstractmethod
    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass


class OllamaProvider(LLMProvider):
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3:8b"):
        self.host = host.rstrip("/")
        self.model = model

    async def is_available(self) -> bool:
        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    @staticmethod
    def _parse_ndjson(raw_line: bytes) -> List[str]:
        line = raw_line.decode("utf-8", errors="ignore").strip()
        if not line:
            return []
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return []
        return [obj.get("message", {}).get("content", "")]

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        url = f"{self.host}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": True}
        headers = {"Content-Type": "application/json"}
        async for delta in _streaming_request(url, payload, headers, self._parse_ndjson):
            yield delta

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        return "".join([c async for c in self.stream(messages)])


class OpenAICompatibleProvider(LLMProvider):
    """Shared implementation for OpenRouter and Groq (OpenAI-compatible SSE)."""

    def __init__(self, base_url: str, api_key: str, model: str, name: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.name = name

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    @staticmethod
    def _parse_sse(raw_line: bytes) -> List[str]:
        line = raw_line.decode("utf-8", errors="ignore").strip()
        if not line.startswith("data:"):
            return []
        data = line[len("data:"):].strip()
        if data == "[DONE]":
            return []
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            return []
        choices = obj.get("choices") or []
        if not choices:
            # Non-final chunks (e.g. usage/role) carry no delta content.
            return []
        return [choices[0].get("delta", {}).get("content", "")]

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "stream": True,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream",
        }
        async for delta in _streaming_request(url, payload, headers, self._parse_sse):
            yield delta

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError(f"{self.name} API Key not set")
        return "".join([c async for c in self.stream(messages)])


class OpenRouterProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.3-70b-instruct"):
        super().__init__(
            "https://openrouter.ai/api/v1", api_key, model, "OpenRouter"
        )


class GroqProvider(OpenAICompatibleProvider):
    """Groq Cloud LLM (OpenAI-compatible chat completions API)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        super().__init__("https://api.groq.com/openai/v1", api_key, model, "Groq")


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI (and OpenAI-compatible) chat completions API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        super().__init__("https://api.openai.com/v1", api_key, model, "OpenAI")


class LocalMockProvider(LLMProvider):
    async def is_available(self) -> bool:
        return True

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        last_user = messages[-1]["content"] if messages else ""
        return (
            f"Raphael Assistant (Local Mode): I received your message: "
            f"'{last_user}'. All system tools and controls are operational."
        )

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        # Local mode has no network latency; yield the canned response as tokens
        # without artificial delays or buffering the full string first.
        res = await self.chat(messages)
        for token in res.split(" "):
            yield token + " "


class LLMRouter:
    def __init__(self):
        self.config = get_config()
        self.providers: Dict[str, LLMProvider] = {}
        self._build_providers()

    def _build_providers(self) -> None:
        self.config = get_config()
        self.providers = {
            "ollama": OllamaProvider(self.config.llm.ollama_host, self.config.llm.ollama_model),
            "groq": GroqProvider(self.config.llm.groq_api_key, self.config.llm.groq_model),
            "openrouter": OpenRouterProvider(self.config.llm.openrouter_api_key, self.config.llm.openrouter_model),
            "openai": OpenAIProvider(self.config.llm.openai_api_key, self.config.llm.openai_model),
            "mock": LocalMockProvider(),
        }

    def rebuild(self) -> None:
        """Re-read configuration and rebuild provider instances (live config change)."""
        self._build_providers()

    async def get_active_provider(self) -> Tuple[str, LLMProvider]:
        primary_name = self.config.llm.primary_provider
        primary = self.providers.get(primary_name)
        if primary and await primary.is_available():
            return primary_name, primary

        fallback_name = self.config.llm.fallback_provider
        fallback = self.providers.get(fallback_name, self.providers["mock"])
        return fallback_name, fallback

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        name, provider = await self.get_active_provider()
        logger.info(f"Routing LLM chat to provider: {name}")
        return await provider.chat(messages)

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        name, provider = await self.get_active_provider()
        logger.info(f"Routing LLM stream to provider: {name}")
        async for chunk in provider.stream(messages):
            yield chunk


_llm_router = LLMRouter()


def get_llm_router() -> LLMRouter:
    return _llm_router
