from fastapi import APIRouter, FastAPI, WebSocket, Depends
from typing import List
from websocket_handler import get_active_websockets, active_websockets

router = APIRouter()



@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            # Keep the connection open and wait for any potential messages
            # (you can also handle incoming messages here)
            await websocket.receive_text()
    except Exception as e:
        # Handle disconnection
        active_websockets.remove(websocket)



        