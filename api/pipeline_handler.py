from typing import List
from uuid import UUID

from gi.repository import Gst, GObject

from pipelines.base import GSTBase
from pipelines.inputs.input import Input
from pipelines.mixers.mixer import Mixer
from pipelines.outputs.output import Output


class PipelineHandler:
    _pipelines: dict[str, List[GSTBase]] = {"inputs": {}, "outputs": {}, "mixers": {}}
    mainloop: GObject.MainLoop

    def __init__(self, initial_pipelines: dict[str, List[GSTBase]]):
        Gst.init()
        self._pipelines = initial_pipelines
        if "inputs" not in self._pipelines.keys():
            self._pipelines["inputs"] = []
        if "outputs" not in self._pipelines.keys():
            self._pipelines["outputs"] = []
        if "mixers" not in self._pipelines.keys():
            self._pipelines["mixers"] = []

        for pl in initial_pipelines.values():
            for pipeline_cls in pl:
                pipeline_cls.build()
                for inner in pipeline_cls.inner_pipelines:
                    inner.set_state(Gst.State.PLAYING)

    def add_pipeline(self, pipeline: GSTBase, start=True):
        if issubclass(pipeline.__class__, Input):
            try:
                pipeline.build()
                self._pipelines["inputs"].append(pipeline)
            except AttributeError:
                pipeline.build()
                self._pipelines["inputs"] = [pipeline]

        elif issubclass(pipeline.__class__, Output):
            try:
                pipeline.build()
                self._pipelines["outputs"].append(pipeline)
            except AttributeError:
                pipeline.build()
                self._pipelines["outputs"] = [pipeline]
        elif issubclass(pipeline.__class__, Mixer):
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

    def get_pipeline(self, type: str, uid: UUID):
        for pipeline in self._pipelines.get(type):
            if pipeline.data.uid == uid:
                return pipeline

        return None
    
    def delete_pipeline(self, type, uid):
        pipeline = self.get_pipeline(type, uid)
        pipeline.set_state(Gst.State.NULL)

        idx = self._pipelines[type].index(pipeline)
        self._pipelines[type].pop(idx)
        del pipeline

    def start(self):
        self.mainloop = GObject.MainLoop()
        self.mainloop.run()
