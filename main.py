import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

from api import app
from config import settings
from pipelines import Pipeline

if __name__ == "__main__":
    # start the api task
    server_config = Config()
    loop = asyncio.new_event_loop()
    loop.create_task(serve(app, server_config))
    main_pipeline = Pipeline("https://static.dev.dorftv.at/overlay.html", "/home/hatsch/Videos/banane.mp4", 1280, 720)
    main_pipeline.build()
    main_pipeline.run()
