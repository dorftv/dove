import json
import threading

import orjson
from fastapi import APIRouter, WebSocket
import asyncio
from uuid import UUID, uuid4

from api.mixers_dtos import mixerBaseDTO, MixerDeleteDTO
from api.input_models import InputDTO, InputDeleteDTO
from api.output_models import OutputDTO, OutputDeleteDTO

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from logger import logger

router = APIRouter()


class ConnectionManager:
    """Thread-safe WebSocket connection manager."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()  # For async context
        self._sync_lock = threading.Lock()  # For sync context

    @property
    def active_connections(self) -> list[WebSocket]:
        """Read-only access to connections list (returns a copy)."""
        return self._connections.copy()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Thread-safe disconnect."""
        with self._sync_lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast(self, channel, data, type=""):
        """Thread-safe broadcast to all connections."""
        if not type:
            if issubclass(data.__class__, InputDTO) or isinstance(data, InputDeleteDTO):
                type = "input"
            elif issubclass(data.__class__, OutputDTO) or isinstance(data, OutputDeleteDTO):
                type = "output"
            elif issubclass(data.__class__, mixerBaseDTO) or isinstance(data, MixerDeleteDTO):
                type = "mixer"

        final_dict = {
            "type": type,
            "channel": channel,
            "data": data.dict() if hasattr(data, 'dict') else data
        }

        message = orjson.dumps(final_dict).decode("utf-8")

        # Get snapshot of connections under lock
        async with self._lock:
            connections = self._connections.copy()

        # Send to all, collect failures
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message)
            except RuntimeError as e:
                if "WebSocket connection is closed" in str(e):
                    disconnected.append(connection)
            except Exception as e:
                # Log but don't crash on send failures
                logger.log(f"WebSocket send failed: {e}", level='WARNING')
                disconnected.append(connection)

        # Clean up disconnected under lock
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self._connections:
                        self._connections.remove(conn)


manager = ConnectionManager()


@staticmethod
async def update_pipe(data, websocket: WebSocket):
    handler: "GSTBase" = websocket.app.state._state["pipeline_handler"]
    pipeline = handler.getpipeline(UUID(data['data']['uid']))
    await pipeline.update(data['data'])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            update = await update_pipe(data, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
