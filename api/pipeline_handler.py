import asyncio
import sys
from typing import List, ClassVar, Any
from uuid import UUID
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

from api.status_dto import PositionDTO
from api.websockets import manager


def is_subclass_str(cls, base_name):
    return base_name in [base.__name__ for base in cls.__bases__]


class PipelineHandler(object):
    _pipelines: dict[str, List["GSTBase"]] = {"inputs": {}, "outputs": {}, "mixers": {}}
    mainloop: GObject.MainLoop

    def __init__(self):
        Gst.init()

        self._pipelines["inputs"] = []
        self._pipelines["outputs"] = []
        self._pipelines["mixers"] = []
        self._tick()

    def _tick(self):
        GLib.timeout_add_seconds(1, lambda: asyncio.run(self.on_tick()))

    async def on_tick(self):
        inputs = self.get_pipelines('inputs')
        if inputs is not None:
            for input in inputs:
                if input.data.type == "playlist":
                    input.get_pipeline().set_state(Gst.State.PLAYING)
                pipeline = input.get_pipeline()
                success, pos =pipeline.query_position(Gst.Format.TIME)
                if success:
                    input.data.position = pos // Gst.SECOND
                    await manager.broadcast("UPDATE",  PositionDTO(uid=input.data.uid, position=input.data.position), type="input")
        self._tick()

    def build(self, initial_pipelines: dict[str, List["GSTBase"]]):
        for pl_type, pipelines in initial_pipelines.items():
            if pl_type in self._pipelines:
                self._pipelines[pl_type].extend(pipelines)
            else:
                self._pipelines[pl_type] = pipelines

        for pl_type in ("inputs", "mixers", "outputs"):
            assert pl_type in self._pipelines
            for pipeline_cls in self._pipelines[pl_type]:
                pipeline_cls.build()
                for inner in pipeline_cls.inner_pipelines:
                    inner.set_state(Gst.State.PLAYING)

    def start(self):
        self.mainloop = GObject.MainLoop()
        self.mainloop.run()

    def add_pipeline(self, pipeline: "GSTBase", start=True):
        if self._pipelines is None:
            self._pipelines = {"inputs": [], "outputs": [], "mixers": []}
        if is_subclass_str(pipeline.__class__, "Input"):
            try:
                pipeline.build()
                self._pipelines["inputs"].append(pipeline)
            except AttributeError:
                pipeline.build()
                self._pipelines["inputs"] = [pipeline]

        elif is_subclass_str(pipeline.__class__, "Output"):
            try:
                pipeline.build()
                self._pipelines["outputs"].append(pipeline)
            except AttributeError:
                pipeline.build()
                self._pipelines["outputs"] = [pipeline]
        elif is_subclass_str(pipeline.__class__, "Mixer"):
            try:
                pipeline.build()
                self._pipelines["mixers"].append(pipeline)
            except AttributeError:
                pipeline.build()
                self._pipelines["mixers"] = [pipeline]
        else:
            raise KeyError("Invalid pipeline type")

        if start:
            for inner in pipeline.inner_pipelines:
                inner.set_state(Gst.State.PLAYING)



    def get_pipelines(self, type):
            if self._pipelines is not None:
                return self._pipelines.get(type)
            else:
                return None

    def get_pipeline(self, type: str, uid: UUID):
        if self._pipelines is not None:
            for pipeline in self._pipelines.get(type):
                if pipeline.data.uid == uid:
                    return pipeline

    # return pipeline by uid
    def getpipeline(self, uid: UUID):
        for pipeline in self._pipelines.get('inputs'):
            if pipeline.data.uid == uid:
                return pipeline
        for pipeline in self._pipelines.get('mixers'):
            if pipeline.data.uid == uid:
                return pipeline
        for pipeline in self._pipelines.get('outputs'):
            if pipeline.data.uid == uid:
                return pipeline
        return None

    def get_preview_pipeline(self, src: UUID):
        for pipeline in self._pipelines.get('outputs'):
            if pipeline.data.src == src and pipeline.data.type == "preview_hls":
                pipeline = self.get_pipeline('outputs', pipeline.data.uid)
                return pipeline

        return None

    def delete_pipeline(self, type, uid):
        pipeline = self.get_pipeline(type, uid)
        pipeline.set_state(Gst.State.NULL)

        idx = self._pipelines[type].index(pipeline)
        self._pipelines[type].pop(idx)
        del pipeline


class HandlerSingleton:
    handler: ClassVar[PipelineHandler] = None

    def __new__(cls):
        from main import ElementsFactory

        if cls.handler is None:
            elements = ElementsFactory()
            pipes = elements.create_pipelines()
            cls.handler = PipelineHandler()
            cls.handler.build(pipes)

        return cls.handler