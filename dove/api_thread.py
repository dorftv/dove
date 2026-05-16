import asyncio
import logging
import re
import threading
from contextlib import asynccontextmanager
from importlib.resources import files as resource_files
from threading import Thread
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

import uvicorn


class SuppressHLSAccessFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return '/preview/hls/' not in msg


class RedactTokenAccessFilter(logging.Filter):
    """Redact ?token=… / &token=… from uvicorn access log URLs."""
    _TOKEN_RE = re.compile(r'([?&])token=[^&\s"]*')

    def filter(self, record):
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str) and 'token=' in args[2]:
            redacted = self._TOKEN_RE.sub(r'\1token=REDACTED', args[2])
            record.args = args[:2] + (redacted,) + args[3:]
        return True

from dove.event_loop_bridge import bridge

from dove.api import mixers
from dove.api import mixer

from dove.api import output_routes
from dove.api import input_routes
from dove.api import encoders as encoder_routes
from dove.api import webrtc_whep
from dove.api import webrtc_whip
from dove.api import websockets
from dove.api import configuration
from dove.api import graphviz
from dove.api import hls_preview
from dove.api import docs
from dove.api import auth as auth_module

from dove.proxy import srtrelay, playlist, ovenmedia, mediamtx, v4l2, files
from dove.proxy import nodecg as nodecg_proxy

from dove.pipeline_handler import PipelineHandler

from dove.config_handler import ConfigReader
from dove.logger import logger
config = ConfigReader()



class APIThread(Thread):
    def __init__(self, pipeline_handler: PipelineHandler):
        super().__init__()
        self.pipeline_handler = pipeline_handler


    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        app.state.pipeline_handler = self.pipeline_handler
        yield


    daemon = True
    name = "API Thread"

    def run(self):
        # Create and register the asyncio event loop with the bridge
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bridge.set_asyncio_loop(loop, threading.current_thread())

        # Startup checks
        auth_config = config.get_auth_config()
        if auth_config.get('enabled') and not auth_config.get('cookie_secret'):
            logger.log("Auth enabled without cookie_secret — sessions won't persist across restarts", level='WARNING')

        fastapi = FastAPI(
            lifespan=self.lifespan,
            docs_url=None,
            openapi_url=None,
            redoc_url=None,
        )

        @fastapi.get("/api/debug/docs", include_in_schema=False,
                     dependencies=[auth_module.require_role("admin")])
        async def _swagger_ui():
            return get_swagger_ui_html(openapi_url="/openapi.json", title="DOVE API")

        @fastapi.get("/openapi.json", include_in_schema=False,
                     dependencies=[auth_module.require_role("admin")])
        async def _openapi():
            return fastapi.openapi()

        fastapi.include_router(auth_module.router, tags=['Auth'])
        fastapi.include_router(configuration.router, tags=['Config'])

        fastapi.include_router(input_routes.router, prefix="/api")
        fastapi.include_router(output_routes.router, prefix="/api")
        fastapi.include_router(encoder_routes.router, prefix="/api", tags=['Encoders'])

        fastapi.include_router(mixers.router, tags=['Mixer'])
        fastapi.include_router(mixer.router, tags=['Mixer'])
        fastapi.include_router(graphviz.router, tags=['Debug'])

        # websockets handler
        fastapi.include_router(websockets.router)
        preview_deps = []
        whip_deps = [auth_module.require_role("user")]
        fastapi.include_router(hls_preview.router, tags=['Preview'], dependencies=preview_deps)
        fastapi.include_router(webrtc_whep.router, tags=['WebRTC Preview'], dependencies=preview_deps)
        fastapi.include_router(webrtc_whip.router, tags=['WebRTC Ingest'], dependencies=whip_deps)
        fastapi.include_router(docs.router, tags=['Docs'])

        # Proxies — only mount when configured
        proxy_deps = [auth_module.require_read()]
        proxy_types = config.get_proxy_types()

        if 'v4l2' in proxy_types or 'alsa' in proxy_types:
            fastapi.include_router(v4l2.router, tags=['Proxy'], dependencies=proxy_deps)
        if 'files' in proxy_types or 'images' in proxy_types:
            fastapi.include_router(files.router, tags=['Proxy'], dependencies=proxy_deps)
        if 'srtrelay' in proxy_types:
            fastapi.include_router(srtrelay.router, tags=['Proxy'], dependencies=proxy_deps)
        if 'ovenmedia' in proxy_types:
            fastapi.include_router(ovenmedia.router, tags=['Proxy'], dependencies=proxy_deps)
        if 'mediamtx' in proxy_types:
            fastapi.include_router(mediamtx.router, tags=['Proxy'], dependencies=proxy_deps)
        if 'playlist' in proxy_types:
            fastapi.include_router(playlist.router, tags=['Proxy'], dependencies=proxy_deps)
        if 'nodecg' in proxy_types:
            fastapi.include_router(nodecg_proxy.router, tags=['NodeCG Proxy'], dependencies=[auth_module.require_role("user")])


        @fastapi.middleware("http")
        async def security_headers(request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            return response

        # serve branding assets
        fastapi.mount("/branding", StaticFiles(directory=str(resource_files("dove") / "assets")), name="branding")

        # serve frontend with StaticFiles
        fastapi.mount("/", StaticFiles(directory=str(resource_files("dove") / "static"), html=True), name="static")



        access_logger = logging.getLogger("uvicorn.access")
        access_logger.addFilter(SuppressHLSAccessFilter())
        access_logger.addFilter(RedactTokenAccessFilter())

        uvicorn_config = uvicorn.Config(fastapi, port=5000, host='0.0.0.0', loop='none', ws_ping_interval=5, ws_ping_timeout=10, ws_max_size=65536, proxy_headers=True, forwarded_allow_ips=config.get_forwarded_allow_ips())
        server = uvicorn.Server(uvicorn_config)
        loop.run_until_complete(server.serve())
