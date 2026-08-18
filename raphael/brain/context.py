"""
Context Manager for Raphael AI Assistant.
Maintains prompt context history and system instructions.
"""

from typing import List, Dict, Any

SYSTEM_PROMPT = """You are Raphael, a lightweight, voice-first AI assistant for PC.
Your responses must be concise, direct, helpful, and polite.
Do not use verbose filler phrases like 'Certainly', 'As an AI', or 'I would be happy to help'.
Give clear, actionable answers."""

class ContextManager:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self._history: List[Dict[str, str]] = []

    def add_user_message(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})
        self._trim()

    def add_assistant_message(self, text: str) -> None:
        self._history.append({"role": "assistant", "content": text})
        self._trim()

    def get_messages(self) -> List[Dict[str, str]]:
        return [{"role": "system", "content": SYSTEM_PROMPT}] + list(self._history)

    def _trim(self) -> None:
        if len(self._history) > self.max_history * 2:
            self._history = self._history[-self.max_history * 2:]

_context_manager = ContextManager()

def get_context_manager() -> ContextManager:
    return _context_manager
