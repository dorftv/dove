import orjson
from fastapi import APIRouter, WebSocket
import asyncio
from uuid import UUID

from api.mixers_dtos import mixerBaseDTO, MixerDeleteDTO
from api.input_models import InputDTO, InputDeleteDTO
from api.output_models import OutputDTO, OutputDeleteDTO
from api.encoder_models import EncoderEntityDTO, EncoderEntityDeleteDTO
from api.auth import is_auth_enabled, _read_cookie, _decode_access_token, _parse_groups, _get_config, _check_api_token
from authlib.jose import JoseError

from fastapi import WebSocketDisconnect, HTTPException

from logger import logger

router = APIRouter()


class ConnectionManager:
    """Thread-safe WebSocket connection manager."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()  # For async context

    @property
    def active_connections(self) -> list[WebSocket]:
        """Read-only access to connections list (returns a copy)."""
        return self._connections.copy()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        """Async disconnect - use async lock since called from async context."""
        async with self._lock:
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
            elif isinstance(data, (EncoderEntityDTO, EncoderEntityDeleteDTO)):
                type = "encoder"

        final_dict = {
            "type": type,
            "channel": channel,
            "data": data.model_dump() if hasattr(data, 'model_dump') else data
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


async def update_pipe(data, websocket: WebSocket):
    handler = websocket.app.state._state["pipeline_handler"]
    uid = data['data']['uid']
    pipeline = handler.getpipeline(UUID(uid))
    if 'audio_filters' in data.get('data', {}) or 'video_filters' in data.get('data', {}):
        logger.log(f"WS filters: uid={uid[:8]}, keys={list(data['data'].keys())}", level='DEBUG')
    if not pipeline:
        logger.log(f"WebSocket update for unknown pipeline {uid}", level='WARNING')
        return
    await pipeline.update(data['data'])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Authenticate WebSocket upgrade via session cookie or Bearer header
    if is_auth_enabled():
        authenticated = False

        # Try session cookie first
        cookie_data = _read_cookie(websocket)
        if cookie_data and cookie_data.get('access_token'):
            try:
                token_data = await _decode_access_token(cookie_data['access_token'])
                websocket.state.user_groups = _parse_groups(token_data)
                authenticated = True
            except (JoseError, HTTPException):
                pass

        # Try Bearer header (for API clients that can't set cookies)
        if not authenticated:
            auth_header = websocket.headers.get('authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                api_user = _check_api_token(token)
                if api_user:
                    websocket.state.user_groups = api_user.groups
                    authenticated = True
                else:
                    try:
                        token_data = await _decode_access_token(token)
                        websocket.state.user_groups = _parse_groups(token_data)
                        authenticated = True
                    except (JoseError, HTTPException):
                        pass

        if not authenticated:
            await websocket.close(code=4001, reason="Not authenticated")
            return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            try:
                await update_pipe(data, websocket)
            except Exception as e:
                logger.log(f"WebSocket message error: {e}", level='ERROR')
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.log(f"WebSocket connection error: {e}", level='WARNING')
    finally:
        await manager.disconnect(websocket)
