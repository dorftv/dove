from uuid import uuid4

import gi
import time
from api.inputs_dtos import InputDTO, TestInputDTO
from api.outputs_dtos import previewHlsOutputDTO
from caps import Caps

gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

from api_thread import APIThread
from pipeline_handler import PipelineHandler
from pipelines.inputs.test_input import TestInput
from pipelines.outputs.preview_hls_output import previewHlsOutput
from startup import createElements


elements = createElements()
pipes = elements.create_mixer()
pipelines = PipelineHandler(pipes)


api = APIThread(pipeline_handler=pipelines)
api.start()

time.sleep(1)


pipelines.start()
