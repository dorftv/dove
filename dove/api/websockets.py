import orjson
from fastapi import APIRouter, WebSocket
import asyncio
from uuid import UUID

from dove.api.mixers_dtos import mixerBaseDTO, MixerDeleteDTO
from dove.api.input_models import InputDTO, InputDeleteDTO
from dove.api.output_models import OutputDTO, OutputDeleteDTO
from dove.api.encoder_models import EncoderEntityDTO, EncoderEntityDeleteDTO
from dove.api.auth import is_auth_enabled, get_current_user
from dove.config_handler import ConfigReader

from fastapi import WebSocketDisconnect

from dove.logger import logger

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
    handler = websocket.app.state.pipeline_handler
    uid = data['data']['uid']
    pipeline = handler.get_pipeline_by_uid(UUID(uid))
    if 'audio_filters' in data.get('data', {}) or 'video_filters' in data.get('data', {}):
        logger.log(f"WS filters: uid={uid[:8]}, keys={list(data['data'].keys())}", level='DEBUG')
    if not pipeline:
        logger.log(f"WebSocket update for unknown pipeline {uid}", level='WARNING')
        return

    # Role check: determine required role from the pipeline's category, not client data
    if is_auth_enabled():
        user_groups = getattr(websocket.state, 'user_groups', [])
        auth_cfg = ConfigReader().get_auth_config()
        groups_map = auth_cfg.get('groups', {})
        admin_group = groups_map.get('admin', 'dove-admin')
        if admin_group not in user_groups:
            # Resolve entity type from pipeline handler, not from client message
            entity_category = handler._get_category(pipeline)
            required_role = 'user'
            if entity_category == 'mixers':
                required_role = 'user'  # slot property updates (volume, alpha, position)
            elif entity_category in ('outputs', 'encoders'):
                required_role = 'outputs'
            required_group = groups_map.get(required_role, required_role)
            if required_group not in user_groups:
                logger.log(f"WS update denied: {entity_category} requires {required_role}", level='WARNING')
                return

            # Lock check: supervisor and admin can bypass
            if hasattr(pipeline.data, 'locked') and pipeline.data.locked:
                supervisor_group = groups_map.get('supervisor', 'dove-supervisor')
                if admin_group not in user_groups and supervisor_group not in user_groups:
                    logger.log("WS update denied: entity is locked", level='WARNING')
                    return

    await pipeline.update(data['data'])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if is_auth_enabled():
        try:
            user = await get_current_user(websocket)
            websocket.state.user_groups = user.groups
        except Exception:
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
