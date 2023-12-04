import gi 
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

from api_thread import APIThread
from pipeline_handler import PipelineHandler
from pipelines.test_pipeline import TestPipeline
from pipelines.overlay import CompositorPipeline, VideoPipeline, InterpipePipeline, WPEPipeline
from pipelines.final import FinalPipeline


api = APIThread()
api.start()

pipelines = PipelineHandler()
pipelines.add_pipeline(FinalPipeline(640, 480))
pipelines.start()
