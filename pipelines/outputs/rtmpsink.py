from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs.rtmpsink import RtmpsinkOutputDTO


class RtmpsinkOutput(Output):
    data: RtmpsinkOutputDTO

    def build(self):

        # @TODO get source element
        pipeline_audio_str = ""
        aenc_str = " voaacenc  ! aacparse ! audio/mpeg, mpegversion=4"

        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        if input.has_audio_or_video("audio"):
                audio_caps = self.get_caps('audio', 'S16LE')
                pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! {audio_caps} ! { aenc_str } ! queue ! mux."

        self.add_pipeline(self.get_video_start() + f" videorate ! videoconvert ! videoscale ! { self.get_caps('video', 'I420') }  ! queue !   "
        f" x264enc { self.data.x264_opts } ! video/x-h264,profile={ self.data.h264_profile } ! queue ! flvmux name=mux ! "
        f" rtmpsink name=sink location={self.data.uri} "
        f" { pipeline_audio_str }")


    def describe(self):
        return self.data
