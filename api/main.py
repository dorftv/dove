from uuid import uuid4

import gi

from models.input import InputTypes

gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

from api_thread import APIThread
from pipeline_handler import PipelineHandler
from pipelines.inputs.test import TestPipeline

pipelines = PipelineHandler()

api = APIThread(pipeline_handler=pipelines)
api.start()

pipelines.add_pipeline(None)
pipelines.start()
