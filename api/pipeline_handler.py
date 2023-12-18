from uuid import UUID

from gi.repository import Gst, GObject

from pipelines.base import GSTBase
from pipelines.inputs.input import Input
from pipelines.outputs.output import Output


class PipelineHandler:
    _pipelines: dict[str, GSTBase] = {}
    mainloop: GObject.MainLoop

    def __init__(self, initial_pipelines: dict[str, GSTBase]):
        Gst.init()
        self._pipelines = initial_pipelines
        for pl in initial_pipelines.values():
            for inner in pl.inner_pipelines:
                inner.set_state(Gst.State.PLAYING)

    def add_pipeline(self, pipeline: GSTBase, start=True):
        if issubclass(pipeline.__class__, Input):
            self._pipelines["inputs"] = pipeline
        elif issubclass(pipeline.__class__, Output):
            self._pipelines["outputs"] = pipeline
        else:
            raise KeyError("Invalid pipeline type")

        if start:
            for inner in pipeline.inner_pipelines:
                inner.set_state(Gst.State.PLAYING)

    def get_pipeline(self, type: str, uid: UUID):
        for pipeline in self._pipelines.get(type):
            if pipeline.uid == uid:
                return pipeline

        raise KeyError("Pipeline was not found")

    def start(self):
        self.mainloop = GObject.MainLoop()
        self.mainloop.run()
