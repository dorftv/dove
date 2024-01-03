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
from pipeline_main import HandlerSingleton


# elements = createElements()
# pipes = elements.create_mixer()
# pipelines = PipelineHandler(pipes)
#
#
# api = APIThread(pipeline_handler=pipelines)
# api.start()

handler = HandlerSingleton()

api = APIThread(pipeline_handler=handler)
api.start()

time.sleep(1)


handler.start()
