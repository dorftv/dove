from typing import List
from fastapi import WebSocket
import json

active_websockets: List[WebSocket] = []

def get_active_websockets():
    return active_websockets

async def ws_message(data: str):
    for websocket in active_websockets:
        await websocket.send_text(str(data))

async def ws_broadcast(type, channel, data):
    if hasattr(data, "json"):
        dataJson = data.json()
    else:
        dataJson = data
    print("websocket sent")
    finalJson = json.dumps({
        "type": type,
        "channel": channel,
        "data": json.loads(data)
    })
    print(finalJson)
    for websocket in active_websockets:
        await websocket.send_text(finalJson)