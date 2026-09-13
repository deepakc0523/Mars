"""
WebSocket endpoint router for live event and state broadcasting.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws.manager import ws_manager

router = APIRouter(tags=["websocket"])

log = logging.getLogger(__name__)


@router.websocket("/events/live")
async def websocket_live_events(websocket: WebSocket) -> None:
    """Live WebSocket channel streaming processed events and world state updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open and receive optional ping messages
            data = await websocket.receive_text()
            log.debug("WebSocket received message from client: %s", data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        log.warning("WebSocket error: %s", exc)
        ws_manager.disconnect(websocket)
