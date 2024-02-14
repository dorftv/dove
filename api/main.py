from uuid import uuid4
import gi
gi.require_version('Gst', '1.0')

from api_thread import APIThread
from pipeline_handler import HandlerSingleton
from elements_factory import ElementsFactory
import asyncio


if __name__ == "__main__":
    handler = HandlerSingleton()
    elements = ElementsFactory(handler)
    asyncio.run(elements.create_pipelines())

    api = APIThread(pipeline_handler=handler)
    api.start()

    handler.start()
