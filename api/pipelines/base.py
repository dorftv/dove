import asyncio
import json
from abc import ABC, abstractmethod
import functools
from gi.repository import Gst, GLib

from typing import Callable, Optional, Any, Type

from orjson import orjson
from pydantic import BaseModel

from api.websockets import manager


class GSTBase(BaseModel):
    inner_pipelines: Optional[list[Gst.Pipeline]] = []
    #attrs: BaseModel

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def describe(self):
        pass

    def add_pipeline(self, pipeline: str | Gst.Pipeline):
        print(pipeline)
        if type(pipeline) == str:
            pipeline = Gst.parse_launch(pipeline)

        self.inner_pipelines.append(pipeline)
        pipeline.set_state(Gst.State.PLAYING)
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", lambda e, b: asyncio.run(self._on_error(e, b))),
        bus.connect("message::state-changed", lambda e, b: asyncio.run(self._on_state_change(e, b)))
        bus.connect("message::eos", lambda e, b: asyncio.run(self._on_eos(e, b)))
        bus.connect("message::info", lambda e, b: asyncio.run(self._on_info(e, b)))
        element = self.get_element_from_pipeline("uridecodebin3")
        if element:
            element.connect('about-to-finish', lambda e : asyncio.run(self._on_about_to_finish(e)))
        
    @staticmethod
    def run_on_master():
        def inner(func: Callable):
            return functools.partial(GLib.idle_add, func)
        return inner

    def set_state(self, state: Gst.State):
        for pipeline in self.inner_pipelines:
            pipeline.set_state(state)
    # event handlers

    def has_audio_or_video(self, audio_or_video: str):
        #  @TODO proper handling
        #  disable audio for now.
        #handler: GSTBase = request.app.state._state["pipeline_handler"]
        #input =   handler.get_pipeline("inputs",self.data.uid)  
        return False
    def get_pipeline(self):
        return self.inner_pipelines[0]

    def get_element_from_pipeline(self, element_name):
        pipeline = self.get_pipeline()
        iterator = pipeline.iterate_elements()
        while True:
            result, element = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            if element.get_factory().get_name() == element_name:
                return element
        return None


    async def _on_about_to_finish(self, playbin):
        playbin.set_property("uri", playbin.get_property('uri'))   

    async def _on_error(self, bus, message):
        err, debug = message.parse_error()
        # await ws_message(orjson.dumps({
        #     "uid": self.uid,
        #     "type": "error",
        #     "message": f"Error:, {err}, {debug}",
        # }))
        await manager.broadcast("ERROR", self.data)

    async def _on_state_change(self, bus, message):

        if isinstance(message.src, Gst.Pipeline):
            old_state, new_state, pending_state = message.parse_state_changed()
            msg = f"Pipeline {message.src.get_name()} state changed from {Gst.Element.state_get_name(old_state)} to {Gst.Element.state_get_name(new_state)}"
            self.data.state = Gst.Element.state_get_name(new_state)

            await manager.broadcast("UPDATE", self.data)

    async def _on_eos(self, bus, message):
        self.data.state = "EOS"
        await manager.broadcast("UPDATE", self.data)

    async def _on_info(self, bus, message):
        # await ws_broadcast(orjson.dumps({
        #     "uid": self.uid,
        #     "type": "info",
        #     "message": str(message)
        # }))
        manager.broadcast("INFO", {"message": str(message)})

    class Config:
        arbitrary_types_allowed = True
