from pathlib import Path
from typing import Optional

from pipelines.outputs.output import Output
from api.outputs_dtos import srtOutputDTO


class srtOutput(Output):
    data: srtOutputDTO

    def build(self):
        
        audio_caps = "audio/x-raw, format=S16LE, layout=(string)interleaved, rate=(int)44100, channels=(int)2"

        # @TODO get source element
        pipeline_audio_str = ""
        if self.has_audio_or_video("audio"):
                pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! {audio_caps} ! voaacenc  ! aacparse ! audio/mpeg, mpegversion=4 ! queue ! mux."


        self.add_pipeline(self.get_video_start() + f"  videoconvert ! videoscale ! videorate  !  "
        f" x264enc key-int-max=30 tune=zerolatency speed-preset=slower  ! video/x-h264,profile=high ! queue ! mpegtsmux name=mux ! "
        f" srtsink name=sink uri={self.data.uri} "
        f" { pipeline_audio_str }")


    def describe(self):
        return self.data
