from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs.srtserversink import SrtserversinkOutputDTO


class SrtserversinkOutput(Output):
    data: SrtserversinkOutputDTO

    def build(self):

        pipeline_audio_str = ""
        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)

        pipeline_audio_str = ""
        if input.has_audio_or_video("audio"):
            audioenc = self.get_audio_encoder_pipeline(self.data.audio_encoder.name)
            pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! { audioenc } "

        video_enc = self.get_video_encoder_pipeline(self.data.video_encoder.name)

        self.add_pipeline(
            f"{self.get_video_start()} videoconvert ! videoscale ! videorate ! {video_enc} ! "
            f""
            f"{self.data.mux.element } {self.data.mux.options } name=mux ! "
            f""
            f" srtserversink name=sink  uri={self.data.uri} mode=2"
            f" { pipeline_audio_str } !"
            f" mux.")

    def describe(self):
        return self.data
