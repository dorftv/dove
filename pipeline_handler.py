import sys
from typing import List, ClassVar, Any
from uuid import UUID
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

from api.input_models import PositionDTO
from api.websockets import manager
from event_loop_bridge import bridge
from logger import logger


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
        GLib.timeout_add_seconds(1, self._tick_callback)

    def _tick_callback(self):
        """GLib callback that schedules the async tick work."""
        bridge.schedule_async(self._on_tick_async())
        return False  # Don't repeat - we reschedule in _on_tick_async

    async def _on_tick_async(self):
        """Async tick handler that runs in asyncio context."""
        inputs = self.get_pipelines('inputs')
        if inputs is not None:
            for input in inputs:
                pipeline = input.get_pipeline()
                if pipeline is None:
                    continue  # Pipeline not built yet
                if input.data.type == "playlist":
                    # Schedule GStreamer state change in GLib context
                    bridge.run_sync_in_glib(
                        lambda p=pipeline: p.set_state(Gst.State.PLAYING)
                    )
                success, pos = pipeline.query_position(Gst.Format.TIME)
                if success:
                    input.data.position = pos // Gst.SECOND
                    await manager.broadcast(
                        "UPDATE",
                        PositionDTO(uid=input.data.uid, position=input.data.position),
                        type="input"
                    )
        # Schedule next tick in GLib context
        bridge.run_sync_in_glib(self._tick)


    def start(self):
        self.mainloop = GObject.MainLoop()
        self.mainloop.run()

    def add_pipeline(self, pipeline: "GSTBase", start=True):
        """Add pipeline - defers build() to GLib thread."""
        if self._pipelines is None:
            self._pipelines = {"inputs": [], "outputs": [], "mixers": []}

        # Determine category
        if is_subclass_str(pipeline.__class__, "Input"):
            category = "inputs"
        elif is_subclass_str(pipeline.__class__, "Output"):
            category = "outputs"
        elif is_subclass_str(pipeline.__class__, "Mixer"):
            category = "mixers"
        else:
            raise KeyError("Invalid pipeline type")

        # Add to list immediately (so API can find it)
        if category not in self._pipelines:
            self._pipelines[category] = []
        self._pipelines[category].append(pipeline)

        # Defer actual build to GLib thread
        bridge.run_sync_in_glib(
            lambda p=pipeline, s=start: self._build_pipeline_sync(p, s)
        )

    def _build_pipeline_sync(self, pipeline: "GSTBase", start: bool):
        """Build pipeline - runs in GLib thread context."""
        try:
            pipeline.build()
            if start and pipeline.inner_pipelines:
                for inner in pipeline.inner_pipelines:
                    inner.set_state(Gst.State.PLAYING)
        except Exception as e:
            logger.log(f"Pipeline build failed: {e}", level='ERROR')
            import traceback
            traceback.print_exc()



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

    async def get_pipeline_by_name(self, type: str, name: str):
        if self._pipelines is not None:
            for pipeline in self._pipelines.get(type):
                if pipeline.data.name == name:
                    return pipeline

    def get_program(self):
        if self._pipelines is not None:
            for pipeline in self._pipelines.get("mixers"):
                if pipeline.data.type == "program":
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
            if pipeline.data.src == src and pipeline.data.is_preview:
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
        if cls.handler is None:
            cls.handler = PipelineHandler()

        return cls.handler