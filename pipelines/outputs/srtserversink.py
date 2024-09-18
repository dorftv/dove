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
        if self.data.audio_codec == "aac":
            aenc_str = " voaacenc  ! aacparse ! audio/mpeg, mpegversion=4"
        if self.data.audio_codec == "mp2":
            aenc_str = f" avenc_mp2 { self.data.audio_opts } ! audio/mpeg,mpegversion=1,layer=2,channels=2,mode=joint-stereo"
        if input.has_audio_or_video("audio"):
                audio_caps = self.get_caps('audio', 'S16LE')
                pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! {audio_caps} ! { aenc_str } ! queue ! mux."

        # @TODO add more options to srtserversink
        self.add_pipeline(self.get_video_start() + f"  videorate ! videoconvert !  videoscale !   { self.get_caps('video', 'I420') }  ! "
        f" x264enc {self.data.x264_opts}  ! video/x-h264,profile={ self.data.h264_profile } ! queue !  "
        f" mpegtsmux name=mux {self.data.mux_opts} ! "
        f" srtserversink name=sink  uri={self.data.uri} mode=2 latency={self.data.latency}"
        f" { pipeline_audio_str }")


    def describe(self):
        return self.data
