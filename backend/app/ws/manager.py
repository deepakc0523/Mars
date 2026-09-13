"""
WebSocket connection manager for real-time live event broadcasting.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts event/state payloads."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept connection and store in active connections list."""
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("WebSocket connected: total=%d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove connection from active list."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info("WebSocket disconnected: total=%d", len(self.active_connections))

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Broadcast a message dict to all connected clients."""
        if not self.active_connections:
            return
        log.debug("Broadcasting WebSocket data to %d clients", len(self.active_connections))
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as exc:
                log.warning("Failed to send WebSocket message, removing client: %s", exc)
                self.disconnect(connection)


ws_manager = ConnectionManager()
