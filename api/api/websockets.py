from fastapi import APIRouter, FastAPI, WebSocket, Depends
from typing import List

from api.inputs_dtos import TestInputDTO, UriInputDTO
from pipelines.base import GSTBase
from websocket_handler import get_active_websockets, active_websockets, ws_broadcast

router = APIRouter()



@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    handler: GSTBase = websocket.app.state._state["pipeline_handler"]

    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            # Keep the connection open and wait for any potential messages
            # (you can also handle incoming messages here)
            data = await websocket.receive_json()
            pipeline = handler.get_pipeline(data.pop("pipeline_type"), data.uid)

            if data.type == "testsrc":
                pipeline.data = TestInputDTO(**data)
            elif data.type == "urisrc":
                pipeline.data = UriInputDTO(**data)

            await ws_broadcast(data)

    except Exception as e:
        # Handle disconnection
        active_websockets.remove(websocket)



        