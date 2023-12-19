from typing import List
from fastapi import WebSocket

active_websockets: List[WebSocket] = []

def get_active_websockets():
    return active_websockets

async def ws_broadcast(data: str):
    for websocket in active_websockets:
        await websocket.send_text(str(data))
