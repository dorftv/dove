from contextlib import asynccontextmanager
from threading import Thread
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import uvicorn
from api import inputs
from api import mixers
from api import mixer

from api import output_routes
from api import websockets
from api import configuration
from api import graphviz
from api import hls_preview

from proxy import srtrelay

from pipeline_handler import PipelineHandler





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
        fastapi = FastAPI(lifespan=self.lifespan)
        fastapi.include_router(configuration.router, tags=['Config'])
        # fastapi.include_router(hls.router)
        fastapi.include_router(inputs.router)

        fastapi.include_router(output_routes.router, prefix="/api")
        #fastapi.include_router(outputs_router, prefix="/api", tags=['outputs'])

        fastapi.include_router(mixers.router, tags=['Mixer'])
        fastapi.include_router(mixer.router, tags=['Mixer'])
        fastapi.include_router(graphviz.router, tags=['Debug'])

        # websockets handler
        fastapi.include_router(websockets.router)
        fastapi.include_router(hls_preview.router, tags=['Preview'])

        #proxies
        fastapi.include_router(srtrelay.router, tags=['Proxy'])

        # serve frontend with StaticFiles
        fastapi.mount("/", StaticFiles(directory="static", html=True), name="static")



        config = uvicorn.Config(fastapi, port=5000, host='0.0.0.0')
        server = uvicorn.Server(config)
        server.run()
