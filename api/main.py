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

uid = uuid4()

input = TestInput(uid="e0866247-0b40-4d1b-9ac6-ac1e5054c28a", data=TestInputDTO(uid="e0866247-0b40-4d1b-9ac6-ac1e5054c28a", volume=1.0, pattern=0))
#output = previewHlsOutput(uid="e0866247-0b40-4d1b-9ac6-ac1e5054c28b", src="e0866247-0b40-4d1b-9ac6-ac1e5054c28a", data=(previewHlsOutputDTO(uid="e0866247-0b40-4d1b-9ac6-ac1e5054c28b", src="e0866247-0b40-4d1b-9ac6-ac1e5054c28a")))
pipelines = PipelineHandler({"inputs": [input]})
#pipelines = PipelineHandler({"outputs": [output]})

api = APIThread(pipeline_handler=pipelines)
api.start()

time.sleep(1)


pipelines.start()
