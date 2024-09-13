from fastapi import APIRouter, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse, RedirectResponse
import httpx
import asyncio
from websockets.exceptions import ConnectionClosed


router = APIRouter()
NODECG_URL = "http://192.168.23.219:9090"  # Adjust this to your NodeCG URL


# CORS middleware function
async def cors_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Apply CORS middleware to each route
def add_cors_middleware(route):
    original_route = route.endpoint
    async def wrapped_route(*args, **kwargs):
        request = kwargs.get('request')
        if request:
            response = await original_route(*args, **kwargs)
            return await cors_middleware(request, lambda _: response)
        return await original_route(*args, **kwargs)
    route.endpoint = wrapped_route

# Apply CORS middleware to all routes
for route in router.routes:
    if not isinstance(route, WebSocket):
        add_cors_middleware(route)


@router.api_route("/bundles/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_bundles(request: Request, path: str):
    return await proxy_request(request, f"/bundles/{path}")

@router.api_route("/assets/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_bundles(request: Request, path: str):
    return await proxy_request(request, f"/assets/{path}")

@router.api_route("/dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_dashboard(request: Request, path: str):
    return await proxy_request(request, f"/dashboard/{path}")

@router.api_route("/node_modules/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_node_modules(request: Request, path: str):
    return await proxy_request(request, f"/node_modules/{path}")

@router.api_route("/socket.io/{path:path}", methods=["GET", "POST"])
async def proxy_socket_io(request: Request, path: str):
    return await proxy_request(request, f"/socket.io/{path}")

@router.get("/socket.js")
async def proxy_socket_js(request: Request):
    return await proxy_request(request, "/socket.js")

@router.get("/nodecg-api.min.js")
async def proxy_nodecg_api_js(request: Request):
    return await proxy_request(request, "/nodecg-api.min.js")

@router.get("/client_registration.js")
async def proxy_client_registration_js(request: Request):
    return await proxy_request(request, "/client_registration.js")

@router.get("/dialog_opener.js")
async def proxy_dialog_opener_js(request: Request):
    return await proxy_request(request, "/dialog_opener.js")

@router.get("/api.js")
async def proxy_api_js(request: Request):
    return await proxy_request(request, "/api.js")

@router.get("/dashboard.js")
async def proxy_dashboard_js(request: Request):
    return await proxy_request(request, "/dashboard.js")

async def proxy_request(request: Request, path: str):
    try:
        async with httpx.AsyncClient(base_url=NODECG_URL, follow_redirects=True, timeout=30.0) as client:
            url = f"{path}?{request.query_params}"
            headers = {key: value for key, value in request.headers.items()
                       if key.lower() not in ('host', 'content-length', 'content-encoding')}

            method = request.method
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, content=await request.body())
            else:
                response = await client.request(method, url, headers=headers, content=await request.body())

            # Handle redirects
            if response.status_code in (301, 302, 303, 307, 308):
                return RedirectResponse(url=response.headers['Location'], status_code=response.status_code)

            # Remove content-encoding header to prevent double encoding
            response_headers = dict(response.headers)
            response_headers.pop('content-encoding', None)
            response_headers.pop('content-length', None)

            return StreamingResponse(
                response.iter_bytes(),
                status_code=response.status_code,
                headers=response_headers
            )
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="Gateway Timeout: The NodeCG server took too long to respond")
    except httpx.NetworkError:
        raise HTTPException(status_code=502, detail="Bad Gateway: Unable to connect to the NodeCG server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.websocket("/socket.io/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async with httpx.AsyncClient() as client:
        try:
            async with client.websocket(f"{NODECG_URL}/socket.io/?{websocket.query_params}") as nodecg_ws:
                async def forward_to_client():
                    try:
                        async for message in nodecg_ws:
                            await websocket.send_text(message)
                    except ConnectionClosed:
                        pass

                async def forward_to_server():
                    try:
                        while True:
                            message = await websocket.receive_text()
                            await nodecg_ws.send_text(message)
                    except ConnectionClosed:
                        pass

                await asyncio.gather(
                    forward_to_client(),
                    forward_to_server()
                )
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            await websocket.close()