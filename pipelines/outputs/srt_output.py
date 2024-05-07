from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs_dtos import srtOutputDTO


class srtOutput(Output):
    data: srtOutputDTO

    def build(self):

        # @TODO get source element
        pipeline_audio_str = ""
        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        if input.has_audio_or_video("audio"):
                pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! {self.get_caps('audio')} ! voaacenc  ! aacparse ! audio/mpeg, mpegversion=4 ! queue ! mux."



        self.add_pipeline(self.get_video_start() + f" videorate ! videoconvert ! videoscale ! { self.get_caps('video') }  !  "
        f" x264enc key-int-max=30 tune=zerolatency speed-preset=slower  ! video/x-h264,profile=high ! queue ! mpegtsmux name=mux ! "
        f" srtsink name=sink uri={self.data.uri} "
        f" { pipeline_audio_str }")


    def describe(self):
        return self.data
