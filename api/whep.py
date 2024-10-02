from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio

from config_handler import ConfigReader
config = ConfigReader()
host, port = config.get_whep_proxy()


router = APIRouter()

MEDIAMTX_URL = f"http://{host}:{port}"

@router.api_route("/whep{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"])
async def proxy_http(
    request: Request,
    path: str,
    authorization: str = Header(None),
    content_length: int = Header(None)
):
    async with httpx.AsyncClient(base_url=MEDIAMTX_URL) as client:
        target_path = path[5:] if path.startswith("/whep") else path
        if not target_path:
            target_path = "/"


        headers = {}

        for key, value in request.headers.items():
            if key.lower() != 'host':
                headers[key] = value

        headers["Host"] = f"{host}:{port}"

        if authorization:
            headers["Authorization"] = authorization
        if content_length is not None:
            headers["Content-Length"] = str(content_length)

        headers["Connection"] = "keep-alive"
        headers["Sec-Fetch-Dest"] = "empty"
        headers["Sec-Fetch-Mode"] = "cors"
        headers["Sec-Fetch-Site"] = "same-origin"
        headers["TE"] = "trailers"

        body = await request.body()

        try:
            response = await client.request(
                method=request.method,
                url=target_path,
                headers=headers,
                content=body,
            )
            return StreamingResponse(
                response.iter_bytes(),
                status_code=response.status_code,
                headers=dict(response.headers),
            )
        except httpx.HTTPStatusError as exc:
            return StreamingResponse(
                exc.response.iter_bytes(),
                status_code=exc.response.status_code,
                headers=dict(exc.response.headers),
            )

@router.websocket("/whep{path:path}")
async def proxy_websocket(websocket: WebSocket, path: str):
    await websocket.accept()

    target_path = path[5:] if path.startswith("/whep") else path
    if not target_path:
        target_path = "/"


    async with httpx.AsyncClient(base_url=MEDIAMTX_URL) as client:
        headers = {}

        for key, value in websocket.headers.items():
            if key.lower() != 'host':
                headers[key] = value

        headers["Host"] = f"{host}:{port}"

        headers["Connection"] = "Upgrade"
        headers["Upgrade"] = "websocket"
        headers["Sec-WebSocket-Version"] = "13"

        async with client.stream("GET", target_path, headers=headers) as response:
            ws = response.extensions['websocket']

            async def forward_to_server():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await ws.send_text(data)
                except WebSocketDisconnect:
                    await ws.close()

            async def forward_to_client():
                try:
                    while True:
                        data = await ws.receive_text()
                        await websocket.send_text(data)
                except WebSocketDisconnect:
                    await websocket.close()

            try:
                await asyncio.gather(forward_to_server(), forward_to_client())
            except Exception as e:
                print(e)
