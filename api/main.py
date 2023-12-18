import gi

from caps import Caps

gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

# from api_thread import APIThread
from pipeline_handler import PipelineHandler
from pipelines.outputs.hls_output import HLSOutput

caps = Caps(None, None)
output = HLSOutput(caps=caps, listen_to="videomixer_out")
pipelines = PipelineHandler({"outputs": output})

# api = APIThread(pipeline_handler=pipelines)
# api.start()

pipelines.start()
