from contextlib import asynccontextmanager
from threading import Thread
from fastapi import FastAPI

import uvicorn
from api import ui
from api import hls
from api import inputs
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
        fastapi.include_router(ui.router)
        fastapi.include_router(hls.router)
        fastapi.include_router(inputs.router)
        config = uvicorn.Config(fastapi, port=5000, host='0.0.0.0')
        server = uvicorn.Server(config)
        server.run()