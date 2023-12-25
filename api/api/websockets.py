import json

import orjson
from fastapi import APIRouter, WebSocket

from api.inputs_dtos import TestInputDTO, UriInputDTO, InputDTO
from api.mixers_dtos import MixerDTO
from api.outputs_dtos import OutputDTO

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, channel, data):
        type = ""
        if issubclass(data.__class__, InputDTO):
            type = "input"
        elif issubclass(data.__class__, OutputDTO):
            type = "output"
        elif issubclass(data.__class__, MixerDTO):
            type = "mixer"

        final_dict = {
            "type": type,
            "channel": channel,
            "data": data.dict()
        }

        for websocket in self.active_connections:
            await websocket.send_text(orjson.dumps(final_dict).decode("utf-8"))


# @router.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     handler: GSTBase = websocket.app.state._state["pipeline_handler"]
#
#     await websocket.accept()
#     active_websockets.append(websocket)
#     try:
#         while True:
#             data = await websocket.receive_json()
#             pipeline = handler.get_pipeline(data.pop("pipeline_type"), data.uid)
#
#             if data.type == "testsrc":
#                 pipeline.data = TestInputDTO(**data)
#             elif data.type == "urisrc":
#                 pipeline.data = UriInputDTO(**data)
#
#             await ws_broadcast(data)
#
#     except Exception as e:
#         # Handle disconnection
#         active_websockets.remove(websocket)

manager = ConnectionManager()
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    handler: "GSTBase" = websocket.app.state._state["pipeline_handler"]
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            pipeline = handler.get_pipeline(data.pop("pipeline_type"), data.uid)

            if data.type == "testsrc":
                pipeline.data = TestInputDTO(**data)
            elif data.type == "urisrc":
                pipeline.data = UriInputDTO(**data)

            await manager.broadcast("CREATED", data)

    except Exception as e:
        # Handle disconnection
        manager.disconnect(websocket)


        