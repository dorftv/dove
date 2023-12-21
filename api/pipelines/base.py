import asyncio
import json
from abc import ABC, abstractmethod
import functools
from gi.repository import Gst, GLib

from typing import Callable, Optional, Any, Type

from orjson import orjson
from pydantic import BaseModel

from websocket_handler import ws_broadcast, ws_message


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

    @staticmethod
    def run_on_master():
        def inner(func: Callable):
            return functools.partial(GLib.idle_add, func)
        return inner

    def set_state(self, state: Gst.State):
        for pipeline in self.inner_pipelines:
            pipeline.set_state(state)

    # event handlers
    async def _on_error(self, bus, message):
        err, debug = message.parse_error()
        await ws_message(orjson.dumps({
            "uid": self.uid,
            "type": "error",
            "message": f"Error:, {err}, {debug}",
        }))

    async def _on_state_change(self, bus, message):
        
        if isinstance(message.src, Gst.Pipeline):
            old_state, new_state, pending_state = message.parse_state_changed()
            msg = f"Pipeline {message.src.get_name()} state changed from {Gst.Element.state_get_name(old_state)} to {Gst.Element.state_get_name(new_state)}"
            self.data.state = Gst.Element.state_get_name(new_state)
            # @TODO need a way to get type [input/output/mixer] of messaging pipeline            
            #if issubclass(self.pipeline.__class__, Input):
            dataJson = self.data.json()
            await ws_broadcast("input", "UPDATE", dataJson)

    async def _on_eos(self, bus, message):
        await ws_message(orjson.dumps({
            "uid": self.uid,
            "type": "eos",
            "message": str(message)
        }))

    async def _on_info(self, bus, message):
        await ws_broadcast(orjson.dumps({
            "uid": self.uid,
            "type": "info",
            "message": str(message)
        }))

    class Config:
        arbitrary_types_allowed = True
