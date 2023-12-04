from threading import Thread
from fastapi import FastAPI

import uvicorn
from api.ui import router


class APIThread(Thread):
    daemon = True
    name = "API Thread"
    def run(self):
        fastapi = FastAPI()
        fastapi.include_router(router)
        config = uvicorn.Config(fastapi, port=5000)
        server = uvicorn.Server(config)
        server.run()