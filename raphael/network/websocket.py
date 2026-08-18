"""
WebSocket Connection Manager for Raphael AI Assistant.
Syncs assistant state, metrics, and streams real-time events to JARVIS UI.
"""

import asyncio
import json
import time
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from raphael.core.event_bus import get_event_bus, Event
from raphael.core.state_manager import get_state_manager
from raphael.core.resource_manager import get_resource_manager
from raphael.core.logging import get_logger

logger = get_logger("network.websocket")

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._subscribed_to_bus = False

    def setup_event_listeners(self) -> None:
        if not self._subscribed_to_bus:
            bus = get_event_bus()
            bus.subscribe_all(self._on_bus_event)
            self._subscribed_to_bus = True
            logger.info("WebSocketManager subscribed to Event Bus")

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected ({len(self.active_connections)} active)")

        # Sync current state to newly connected client (Section 50)
        state_mgr = get_state_manager()
        res_mgr = get_resource_manager()

        sync_payload = {
            "type": "assistant.state",
            "state": state_mgr.current_state.value,
            "timestamp": time.time(),
            "metrics": res_mgr.get_system_metrics(),
            "metadata": state_mgr.get_summary()
        }
        await websocket.send_text(json.dumps(sync_payload))

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected ({len(self.active_connections)} remaining)")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        if not self.active_connections:
            return

        payload_str = json.dumps(message)
        disconnected = set()

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error broadcasting to client: {e}")
                disconnected.add(connection)

        for dead in disconnected:
            self.disconnect(dead)

    async def _on_bus_event(self, event: Event) -> None:
        payload = {
            "type": event.type,
            "timestamp": event.timestamp,
            "source": event.source,
            **event.data
        }
        await self.broadcast(payload)

_ws_manager = WebSocketManager()

def get_ws_manager() -> WebSocketManager:
    return _ws_manager
