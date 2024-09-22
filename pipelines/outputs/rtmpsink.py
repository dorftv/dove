from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs.rtmpsink import rtmpsinkOutputDTO


class rtmpsinkOutput(Output):
    data: rtmpsinkOutputDTO

    def build(self):

        # @TODO get source element
        pipeline_audio_str = ""
        aenc_str = " voaacenc  ! aacparse ! audio/mpeg, mpegversion=4"

        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        pipeline_audio_str = ""
        pipeline_video_str = ""


        if input.has_audio_or_video("audio"):
            audioenc = self.get_audio_encoder_pipeline(self.data.audio_encoder.name)
            pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! { audioenc } ! queue "

        # @TODO improve has_audio_or_video
        #if input.has_audio_or_video("video") or input.data.type == "playlist":
        videoenc = self.get_video_encoder_pipeline(self.data.video_encoder.name)
        pipeline_video_str = self.get_video_start() +  f" videoconvert ! videoscale ! videorate ! { videoenc } ! queue "

        self.add_pipeline(f"{pipeline_video_str} ! "
        f""
        f"{self.data.mux.element } name={self.data.mux.name} { self.data.mux.options} ! "
        f""
        f"rtmpsink name=sink location={self.data.uri} "
        f""
        f" { pipeline_audio_str } !  {self.data.mux.name}.")


    def describe(self):
        return self.data
