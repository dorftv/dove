from abc import ABC, abstractmethod
import functools
from gi.repository import Gst, GLib

from typing import Callable, Optional, Any

from pydantic import BaseModel

from caps import Caps


class GSTBase(BaseModel):
    inner_pipelines: Optional[list[Gst.Pipeline]] = []
    caps: Caps
    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def describe(self):
        pass

    def add_pipeline(self, pipeline: str | Gst.Pipeline):
        print("pl", pipeline)
        if type(pipeline) == str:
            pipeline = Gst.parse_launch(pipeline)

        self.inner_pipelines.append(pipeline)
        pipeline.set_state(Gst.State.PLAYING)

    @staticmethod
    def run_on_master():
        def inner(func: Callable):
            return functools.partial(GLib.idle_add, func)
        return inner

    def set_state(self, state: Gst.State):
        for pipeline in self.inner_pipelines:
            pipeline.set_state(state)

    class Config:
        arbitrary_types_allowed = True
