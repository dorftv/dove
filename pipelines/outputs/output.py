from abc import ABC
from uuid import UUID
from gi.repository import Gst

from api.output_models import OutputDTO

from pipelines.base import GSTBase


class Output(GSTBase, ABC):
    data: OutputDTO
    def get_video_start(self) -> str:
        return f" interpipesrc name=video_{self.data.uid} listen-to=video_{self.data.src} is-live=true format=time allow-renegotiation=true stream-sync=restart-ts leaky-type=downstream ! "
    def get_audio_start(self):
        return f" interpipesrc name=audio_{self.data.uid} listen-to=audio_{self.data.src} is-live=true format=time allow-renegotiation=true stream-sync=restart-ts leaky-type=downstream ! "

    def get_video_encoder_pipeline(self, encoder) -> str:
        if encoder is None:
            return None

        video_encoder = self.data.video_encoder
        caps = f"{ self.get_caps('video')}"

        if encoder == "x264":
            video_profile_str = f",profile={video_encoder.profile}" if video_encoder.profile else ""
            enc_str = f"{video_encoder.element} {video_encoder.options} ! video/x-h264{video_profile_str}"
            pipeline_str = f"{self.get_caps('video', 'I420')} ! { enc_str } ! h264parse  ! queue "

        elif encoder == "vah264enc" or encoder == "vaapih264enc":
            video_profile_str = f",profile={video_encoder.profile}" if video_encoder.profile else ""
            pipeline_str = f"{ caps } ! vapostproc ! { video_encoder.element } {video_encoder.options } ! video/x-h264{video_profile_str} "

        elif encoder == "openh264enc":
            pipeline_str = f"{self.get_caps('video', 'I420')} ! { video_encoder.element } {video_encoder.options }"

        elif encoder == "mpph264enc":
            pipeline_str = f"{self.get_caps('video', 'I420')} ! { video_encoder.element } {video_encoder.options }"
        return pipeline_str

    def get_audio_encoder_pipeline(self, encoder) -> str:
        if encoder is None:
            return None

        audio_encoder = self.data.audio_encoder
        caps = f"{ self.get_caps('audio')}"

        if encoder == "aac":
            caps = f"{ self.get_caps('audio', 'S16LE')}"
            pipeline_str = f"{ caps } ! { audio_encoder.element }  ! aacparse ! queue "

        elif encoder == "mp2":
            caps =  audio_caps = self.get_caps('audio', 'S16LE')
            #caps = "audio/x-raw,format=S16LE,layout=interleaved,rate=41000,channels=2"
            pipeline_str = f"{ caps } ! { audio_encoder.element }  { audio_encoder.options } ! audio/mpeg,mpegversion=1,layer=2,channels=2,mode=joint-stereo  ! queue "

        elif encoder == "mp3":
            caps = f"{ self.get_caps('audio', 'S16LE')}"
            pipeline_str = f"{ caps } !  { audio_encoder.element }  { audio_encoder.options } ! queue "

        elif encoder == "opus":
            caps = f"{ self.get_caps('audio', 'S16LE')}"
            pipeline_str = f" audio/x-raw,format=S16LE,layout=interleaved,channels=1,rate=24000 ! audioresample !   { audio_encoder.element }  { audio_encoder.options } perfect-timestamp=true frame-size=5 "


        return pipeline_str

    def describe(self):
        return self
