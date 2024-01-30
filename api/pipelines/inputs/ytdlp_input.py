from api.inputs_dtos import ytDlpInputDTO
from .input import Input
from gi.repository import Gst, GLib

from pipelines.description import Description
from pipelines.inputs.input import Input
import json

import yt_dlp

class ytDlpInput(Input):
    data: ytDlpInputDTO

    def build(self):
        videosink_bin = Gst.parse_bin_from_description(self.get_video_end(), True)
        audiosink_bin = Gst.parse_bin_from_description(self.get_audio_end(), True)
        playbin = Gst.ElementFactory.make("playbin3", "playbin")
        playbin.set_property("uri", f"{self.extract_video_url(self.data.uri)}")
        playbin.set_property("instant-uri", True)
        playbin.set_property("video-sink", videosink_bin)
        playbin.set_property("audio-sink", audiosink_bin)
        # @TODO add config option for buffer
        playbin.set_property('buffer-duration', 1 * Gst.SECOND)
        self.add_pipeline(playbin)

    def _on_eos(self, bus, message):
        if self.data.loop:
            playbin = self.get_pipeline()
            playbin.set_property("uri", playbin.get_property('uri'))
            playbin.set_state(Gst.State.PLAYING)
        else:
            super()._on_eos(bus, message)

    def extract_video_url(self, youtube_url):
        ydl_opts = {
            'format': 'best',  # @TODO make selectable
            'quiet': True,
            'no_warnings': True,
            'force_generic_extractor': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            video_url = info_dict.get("url", None)
            return video_url

    def describe(self):

        return self.data



