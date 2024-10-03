from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs.rtspclientsink import rtspclientsinkOutputDTO


class rtspclientsinkOutput(Output):
    data: rtspclientsinkOutputDTO

    def build(self):
        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)

        pipeline_audio_str = ""
        if True:
        #if input.has_audio_or_video("audio"):
            audioenc = self.get_audio_encoder_pipeline(self.data.audio_encoder.name)
            pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! { audioenc } "

        video_enc = self.get_video_encoder_pipeline(self.data.video_encoder.name)

        self.add_pipeline(
            f"rtspclientsink name=sink location={self.data.location} "
            f"{self.get_video_start()} videoconvert ! videoscale ! videorate ! {video_enc} ! sink.sink_0 "
            f""
            f"{pipeline_audio_str} ! "
            f""
            f"sink.sink_1 "
        )


    def describe(self):
        return self.data
