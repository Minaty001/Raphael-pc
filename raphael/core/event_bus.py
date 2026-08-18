"""
Asynchronous Event Bus for Raphael AI Assistant.
Decouples modules using pub/sub event architecture.
Supports string event types and dictionary payload inputs.
"""

import asyncio
import time
from typing import Dict, List, Callable, Awaitable, Any, Optional, Union
from dataclasses import dataclass, field
from raphael.core.logging import get_logger

logger = get_logger("event_bus")

@dataclass
class Event:
    type: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "core"

EventHandler = Callable[[Event], Awaitable[None]]

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._global_subscribers: List[EventHandler] = []
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed handler to {event_type}")

    def subscribe_all(self, handler: EventHandler) -> None:
        if handler not in self._global_subscribers:
            self._global_subscribers.append(handler)
            logger.debug("Subscribed handler to all events")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_or_type: Union[str, Dict[str, Any]], data: Optional[Dict[str, Any]] = None, source: str = "core") -> Event:
        if isinstance(event_or_type, dict):
            event_type = event_or_type.get("type", "unknown.event")
            event_data = {k: v for k, v in event_or_type.items() if k != "type"}
            if data:
                event_data.update(data)
        else:
            event_type = str(event_or_type)
            event_data = data or {}

        event = Event(type=event_type, data=event_data, timestamp=time.time(), source=source)
        logger.debug(f"Event Published: {event_type} | Source: {source}")

        handlers = list(self._subscribers.get(event_type, [])) + list(self._global_subscribers)
        
        if handlers:
            tasks = []
            for handler in handlers:
                try:
                    res = handler(event)
                    if asyncio.iscoroutine(res):
                        tasks.append(asyncio.create_task(res))
                except Exception as e:
                    logger.error(f"Error invoking event handler for {event_type}: {e}", exc_info=True)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        return event

_global_event_bus = EventBus()

def get_event_bus() -> EventBus:
    return _global_event_bus
