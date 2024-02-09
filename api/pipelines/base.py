import asyncio
import json
from abc import ABC, abstractmethod
import functools
from gi.repository import Gst, GLib

from typing import Callable, Optional, Any, Type

from orjson import orjson
from pydantic import BaseModel

from api.websockets import manager
from api.inputs_dtos import InputDTO


class GSTBase(BaseModel):
    inner_pipelines: Optional[list[Gst.Pipeline]] = []

    # attrs: BaseModel

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def describe(self):
        pass

    def add_pipeline(self, pipeline: str | Gst.Pipeline):
        if type(pipeline) == str:
            pipeline = Gst.parse_launch(pipeline)

        if pipeline is None:
            return
        self.inner_pipelines.append(pipeline)
        pipeline.set_name(str(self.data.uid))
        pipeline.set_state(Gst.State.PLAYING)
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", lambda b, m: self.run_on_master(self._on_error, b, m)),
        bus.connect("message::state-changed", lambda b, m: self.run_on_master(self._on_state_change, b, m))
        bus.connect("message::eos", lambda b, m: self.run_on_master(self._on_eos, b, m))
        bus.connect("message::info", lambda b, m: self.run_on_master(self._on_info, b, m))


    def run_on_master(self, func: Callable, *args):
        return GLib.idle_add(func, *args)

    def get_pipeline(self):
        return self.inner_pipelines[0]

    def set_state(self, state: Gst.State):
        for pipeline in self.inner_pipelines:
            pipeline.set_state(state)

    def has_audio_or_video(self, audio_or_video: str):
        pipeline = self.get_pipeline()
        iterator = pipeline.iterate_elements()
        while True:
            result, element = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            pads = element.pads
            for pad in pads:
                caps = pad.get_current_caps()

                if caps:
                    for i in range(caps.get_size()):
                        structure = caps.get_structure(i)
                        if structure and structure.get_name().startswith(audio_or_video):
                            return True
        return False

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

    def _on_error(self, bus, message):
        err, debug = message.parse_error()

        self.data.state = "ERROR"
        asyncio.run(manager.broadcast("UPDATE", self.data))


    def _on_state_change(self, bus, message):
        if isinstance(message.src, Gst.Pipeline):
            old_state, new_state, pending_state = message.parse_state_changed()
            msg = f"Pipeline {message.src.get_name()} state changed from {Gst.Element.state_get_name(old_state)} to {Gst.Element.state_get_name(new_state)}"
            self.data.state = Gst.Element.state_get_name(new_state)
            if issubclass(self.data.__class__, InputDTO) and self.data.state == "PAUSED":
                self.add_preview()
                pipeline = self.get_pipeline()
                duration = (pipeline.query_duration(Gst.Format.TIME).duration // Gst.SECOND)
                if duration and duration != -1:
                    self.data.duration = duration
            asyncio.run(manager.broadcast("UPDATE", self.data))

    def _on_eos(self, bus, message):
        self.data.state = "EOS"
        asyncio.run(manager.broadcast("UPDATE", self.data))

    def _on_info(self, bus, message):
        # await ws_broadcast(orjson.dumps({
        #     "uid": self.uid,
        #     "type": "info",
        #     "message": str(message)
        # }))
        asyncio.run(manager.broadcast("INFO", {"message": str(message)}))

    class Config:
        arbitrary_types_allowed = True
