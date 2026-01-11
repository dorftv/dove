import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from threading import Thread
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import uvicorn


class SuppressHLSAccessFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return '/preview/hls/' not in msg

from event_loop_bridge import bridge

from api import mixers
from api import mixer

from api import output_routes
from api import input_routes
from api import encoders as encoder_routes
from api import webrtc_whep
from api import webrtc_whip
from api import websockets
from api import configuration
from api import graphviz
from api import hls_preview
from api import docs
from api import auth as auth_module

from proxy import srtrelay, playlist, ovenmedia, mediamtx, v4l2, files
from proxy import nodecg as nodecg_proxy

from pipeline_handler import PipelineHandler

from config_handler import ConfigReader
from logger import logger
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

        fastapi = FastAPI(lifespan=self.lifespan, docs_url="/api/debug/docs", redoc_url=None)
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
        preview_deps = [auth_module.require_role("user")]
        fastapi.include_router(hls_preview.router, tags=['Preview'], dependencies=preview_deps)
        fastapi.include_router(webrtc_whep.router, tags=['WebRTC Preview'], dependencies=preview_deps)
        fastapi.include_router(webrtc_whip.router, tags=['WebRTC Ingest'], dependencies=preview_deps)

        fastapi.include_router(docs.router, tags=['Docs'])

        # Proxies — only mount when configured
        proxy_deps = [auth_module.require_role("user")]
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
            fastapi.include_router(nodecg_proxy.router, tags=['NodeCG Proxy'], dependencies=proxy_deps)


        @fastapi.middleware("http")
        async def security_headers(request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            return response

        # serve branding assets
        fastapi.mount("/branding", StaticFiles(directory="assets"), name="branding")

        # serve frontend with StaticFiles
        fastapi.mount("/", StaticFiles(directory="static", html=True), name="static")



        logging.getLogger("uvicorn.access").addFilter(SuppressHLSAccessFilter())

        uvicorn_config = uvicorn.Config(fastapi, port=5000, host='0.0.0.0', loop='none', ws_ping_interval=5, ws_ping_timeout=10)
        server = uvicorn.Server(uvicorn_config)
        loop.run_until_complete(server.serve())
