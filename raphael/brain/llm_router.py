"""
LLM Router and Unified Provider Interface for Raphael AI Assistant.
Supports Ollama, OpenRouter, Groq, OpenAI-compatible APIs, and local mock fallbacks.
"""

import asyncio
import json
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, List, AsyncGenerator, Optional, Tuple
from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("brain.llm_router")

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

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

        def _do_request():
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                res_body = resp.read().decode("utf-8")
                parsed = json.loads(res_body)
                return parsed.get("message", {}).get("content", "")

        return await asyncio.to_thread(_do_request)

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        full_res = await self.chat(messages)
        words = full_res.split(" ")
        for w in words:
            yield w + " "
            await asyncio.sleep(0.03)

class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.3-70b-instruct"):
        self.api_key = api_key
        self.model = model

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API Key not set")

        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        def _do_request():
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                res_body = resp.read().decode("utf-8")
                parsed = json.loads(res_body)
                choices = parsed.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""

        return await asyncio.to_thread(_do_request)

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        full_res = await self.chat(messages)
        for chunk in full_res.split(" "):
            yield chunk + " "
            await asyncio.sleep(0.02)

class GroqProvider(LLMProvider):
    """Groq Cloud LLM (OpenAI-compatible chat completions API)."""
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def is_available(self) -> bool:
        # Free-tier Groq models are gated only by a valid key.
        return bool(self.api_key and len(self.api_key) > 10)

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise ValueError("Groq API Key not set (set GROQ_API_KEY env or .env)")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")

        def _do_request() -> str:
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                res_body = resp.read().decode("utf-8")
                parsed = json.loads(res_body)
                choices = parsed.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                # Surface API-level errors instead of returning empty silently.
                if "error" in parsed:
                    raise RuntimeError(f"Groq API error: {parsed['error']}")
                return ""

        return await asyncio.to_thread(_do_request)

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        full_res = await self.chat(messages)
        for chunk in full_res.split(" "):
            yield chunk + " "
            await asyncio.sleep(0.02)


class LocalMockProvider(LLMProvider):
    async def is_available(self) -> bool:
        return True

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        last_user = messages[-1]["content"] if messages else ""
        return f"Raphael Assistant (Local Mode): I received your message: '{last_user}'. All system tools and controls are operational."

    async def stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        res = await self.chat(messages)
        for token in res.split(" "):
            yield token + " "
            await asyncio.sleep(0.04)

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
            "mock": LocalMockProvider()
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
