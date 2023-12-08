from threading import Thread
from fastapi import FastAPI

import uvicorn
from api import ui
from api import hls


class APIThread(Thread):
    daemon = True
    name = "API Thread"
    def run(self):
        fastapi = FastAPI()
        fastapi.include_router(ui.router)
        fastapi.include_router(hls.router)
        config = uvicorn.Config(fastapi, port=5000, host='0.0.0.0')
        server = uvicorn.Server(config)
        server.run()