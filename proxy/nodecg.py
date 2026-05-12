"""Reverse proxy for NodeCG — mounts at root level so iframes work with
root-relative URLs (/bundles/..., /socket.io/, /assets/...).

Only registered when [proxy.nodecg] config or NODECG_URL env var is set.
"""

import asyncio

import httpx
import websockets
from fastapi import APIRouter, Request, WebSocket, HTTPException
from fastapi.responses import Response

from api.auth import is_auth_enabled, get_current_user
from config_handler import ConfigReader
from logger import logger

config = ConfigReader()
router = APIRouter()

_nodecg_url = ""
_http_client = None


def _get_url() -> str:
    global _nodecg_url
    if not _nodecg_url:
        cfg = config.get_nodecg_config()
        _nodecg_url = cfg['url'] if cfg else ""
    return _nodecg_url


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(follow_redirects=False, timeout=30.0)
    return _http_client


# --- HTTP proxy core ---

async def _proxy(request: Request, path: str) -> Response:
    url = _get_url()
    if not url:
        raise HTTPException(status_code=502, detail="NodeCG not configured")

    target = f"{url}{path}"
    if request.query_params:
        target += f"?{request.query_params}"

    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ('host', 'content-length', 'content-encoding')}

    try:
        client = _get_client()
        body = await request.body() if request.method != "GET" else None
        resp = await client.request(request.method, target, headers=headers, content=body)

        resp_headers = dict(resp.headers)
        resp_headers.pop('content-encoding', None)
        resp_headers.pop('content-length', None)
        resp_headers.pop('transfer-encoding', None)

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=resp_headers,
        )
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise HTTPException(status_code=502, detail="NodeCG unreachable")
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="NodeCG timeout")


# --- Routes ---

@router.api_route("/bundles/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_bundles(request: Request, path: str):
    return await _proxy(request, f"/bundles/{path}")


@router.api_route("/assets/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_assets(request: Request, path: str):
    return await _proxy(request, f"/assets/{path}")


@router.api_route("/dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_dashboard(request: Request, path: str):
    return await _proxy(request, f"/dashboard/{path}")


@router.api_route("/node_modules/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_node_modules(request: Request, path: str):
    return await _proxy(request, f"/node_modules/{path}")


@router.api_route("/socket.io/{path:path}", methods=["GET", "POST"])
async def proxy_socket_io(request: Request, path: str):
    return await _proxy(request, f"/socket.io/{path}")


@router.get("/socket.js")
async def proxy_socket_js(request: Request):
    return await _proxy(request, "/socket.js")


@router.get("/nodecg-api.min.js")
async def proxy_nodecg_api_js(request: Request):
    return await _proxy(request, "/nodecg-api.min.js")


@router.get("/client_registration.js")
async def proxy_client_registration_js(request: Request):
    return await _proxy(request, "/client_registration.js")


@router.get("/dialog_opener.js")
async def proxy_dialog_opener_js(request: Request):
    return await _proxy(request, "/dialog_opener.js")


@router.get("/api.js")
async def proxy_api_js(request: Request):
    return await _proxy(request, "/api.js")


@router.get("/dashboard.js")
async def proxy_dashboard_js(request: Request):
    return await _proxy(request, "/dashboard.js")


# --- WebSocket proxy for socket.io ---

@router.websocket("/socket.io/")
async def ws_proxy(client_ws: WebSocket):
    if is_auth_enabled():
        try:
            user = await get_current_user(client_ws)
        except Exception:
            await client_ws.close(code=4001, reason="Not authenticated")
            return
        auth_cfg = config.get_auth_config()
        groups_map = auth_cfg.get('groups', {})
        admin_group = groups_map.get('admin', 'dove-admin')
        user_group = groups_map.get('user', 'dove-user')
        if admin_group not in user.groups and user_group not in user.groups:
            await client_ws.close(code=4003, reason="Insufficient permissions")
            return

    url = _get_url()
    if not url:
        await client_ws.close(code=1008, reason="NodeCG not configured")
        return

    ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
    target = f"{ws_url}/socket.io/?{client_ws.query_params}"

    await client_ws.accept()
    try:
        async with websockets.connect(target) as server_ws:
            async def client_to_server():
                try:
                    while True:
                        data = await client_ws.receive_text()
                        await server_ws.send(data)
                except Exception:
                    pass

            async def server_to_client():
                try:
                    async for msg in server_ws:
                        if isinstance(msg, str):
                            await client_ws.send_text(msg)
                        else:
                            await client_ws.send_bytes(msg)
                except Exception:
                    pass

            await asyncio.gather(client_to_server(), server_to_client())
    except Exception as e:
        logger.log(f"NodeCG WebSocket proxy error: {e}", level='WARNING')
    finally:
        try:
            await client_ws.close()
        except Exception:
            pass
