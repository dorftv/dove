from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs.srtsink import SrtsinkOutputDTO


class SrtsinkOutput(Output):
    data: SrtsinkOutputDTO

    def build(self):

        # @TODO get source element
        pipeline_audio_str = ""
        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        if self.data.audio_codec == "aac":
            aenc_str = " voaacenc  ! aacparse ! audio/mpeg, mpegversion=4"
        if input.has_audio_or_video("audio"):
                audio_caps = self.get_caps('audio', 'S16LE')
                pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! {audio_caps} ! { aenc_str } ! mux."

        self.add_pipeline(self.get_video_start() + f"  videorate ! videoconvert !  videoscale !   { self.get_caps('video', 'I420') }  ! "
        f" x264enc {self.data.x264_opts}  ! video/x-h264,profile={ self.data.h264_profile } ! queue !  mpegtsmux name=mux ! "
        f" srtsink name=sink uri={self.data.uri} "
        f" { pipeline_audio_str }")


    def describe(self):
        return self.data
