import asyncio
import json
from abc import ABC, abstractmethod
import functools
from gi.repository import Gst, GLib

from typing import Callable, Optional, Any, Type

from orjson import orjson
from pydantic import BaseModel

from caps import Caps
from websocket_handler import ws_broadcast


class GSTBase(BaseModel):
    inner_pipelines: Optional[list[Gst.Pipeline]] = []
    caps: Caps
    #attrs: BaseModel

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def describe(self):
        pass

    def add_pipeline(self, pipeline: str | Gst.Pipeline):
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
        await ws_broadcast(orjson.dumps({
            "uid": self.uid,
            "type": "error",
            "message": str(message)
        }))

    async def _on_state_change(self, bus, message):
        if isinstance(message.src, Gst.Pipeline):
            old_state, new_state, pending_state = message.parse_state_changed()
            msg = f"Pipeline {message.src.get_name()} state changed from {Gst.Element.state_get_name(old_state)} to {Gst.Element.state_get_name(new_state)}"
            await ws_broadcast(orjson.dumps({
                "uid": self.uid,
                "type": "state_change",
                "message": str(msg)
        }))

    async def _on_eos(self, bus, message):
        await ws_broadcast(orjson.dumps({
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
