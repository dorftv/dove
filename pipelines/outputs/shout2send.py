
from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs.shout2send import Shout2sendOutputDTO


class Shout2sendOutput(Output):
    data: Shout2sendOutputDTO

    def build(self):
        pipeline_audio_str = ""
        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        if input.has_audio_or_video("audio"):
            #@TODO: Add option for oggenc
            self.add_pipeline(self.get_audio_start() + f"  audioconvert ! audioresample ! audio/x-raw,rate=44100,channels=1 ! "
                f"lamemp3enc target=bitrate bitrate=192  ! "
                f"shout2send mount={self.data.mount} port={self.data.port} username={self.data.username} password={self.data.password} ip={self.data.ip} "
                f"sync=true")

    def describe(self):
        return self.data


