from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import StreamingResponse

import httpx

router = APIRouter()

NODECG_URL = "http://192.168.23.219:9090"  # Adjust this to your NodeCG URL

@router.api_route("/nodecg/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_nodecg(request: Request, path: str):
    client = httpx.AsyncClient(base_url=NODECG_URL)
    url = f"/{path}"

    headers = {key: value for key, value in request.headers.items() if key.lower() != "host"}

    req = client.build_request(request.method, url, headers=headers, content=await request.body())
    response = await client.send(req, stream=True)

    return StreamingResponse(
        response.aiter_raw(),
        status_code=response.status_code,
        headers=response.headers
    )

# Specific route for WebSocket connections
@router.websocket("/nodecg/socket.io")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async with httpx.AsyncClient(base_url=NODECG_URL) as client:
        async with client.stream("GET", "/socket.io", headers=websocket.headers) as response:
            async for chunk in response.aiter_bytes():
                await websocket.send_bytes(chunk)
