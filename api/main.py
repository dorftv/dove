from uuid import uuid4

import gi

from api.dtos import InputDTO, TestInputDTO
from caps import Caps

gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

from api_thread import APIThread
from pipeline_handler import PipelineHandler
from pipelines.inputs.test_input import TestInput

caps = Caps(video="video/x-raw,width=1280,height=720,framerate=25/1", audio="audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2")
uid = uuid4()

input = TestInput(caps=caps, uid=uid, dto=TestInputDTO(volume=1.0))
pipelines = PipelineHandler({"inputs": [input]})

api = APIThread(pipeline_handler=pipelines)
api.start()

pipelines.start()
