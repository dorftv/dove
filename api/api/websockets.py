import json

import orjson
from fastapi import APIRouter, WebSocket
import asyncio
from uuid import UUID, uuid4

from api.mixers_dtos import mixerDTO, MixerDeleteDTO
from api.inputs_dtos import InputDTO, InputDeleteDTO
from api.outputs_dtos import OutputDTO, OutputDeleteDTO

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

router = APIRouter()



class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
  
    async def broadcast(self, channel, data, type=""):
        if not type:
            if issubclass(data.__class__, InputDTO) or isinstance(data, InputDeleteDTO):
                type = "input"
            elif issubclass(data.__class__, OutputDTO) or isinstance(data, OutputDeleteDTO):
                type = "output"
            elif issubclass(data.__class__, mixerDTO) or isinstance(data, MixerDeleteDTO):
                type = "mixer"

        final_dict = {
            "type": type,
            "channel": channel,
            "data": data.dict()
        }        
        for connection in self.active_connections:
            await connection.send_text(orjson.dumps(final_dict).decode("utf-8"))



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
