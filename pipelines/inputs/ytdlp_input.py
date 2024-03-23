from api.inputs_dtos import ytDlpInputDTO
from .input import Input
from gi.repository import Gst, GLib
from logger import logger

from pipelines.description import Description
from pipelines.inputs.input import Input
import json

import yt_dlp

class ytDlpInput(Input):
    data: ytDlpInputDTO

    def build(self):
        videosink_bin = Gst.parse_bin_from_description(f"videoconvert ! video/x-raw,format=BGRA ! queue ! {self.get_video_end()}", True)
        audiosink_bin = Gst.parse_bin_from_description(self.get_audio_end(), True)
        playbin = Gst.ElementFactory.make("playbin3", "playbin")
        playbin.set_property("uri", f"{self.extract_video_url(self.data.uri)}")
        playbin.set_property("video-sink", videosink_bin)
        playbin.set_property("audio-sink", audiosink_bin)
        # @TODO add config option for buffer
        playbin.set_property('buffer-duration', 5 * Gst.SECOND)
        playbin.connect('element-setup', self.on_element_setup)
        self.add_pipeline(playbin)

    # @TODO inherit functions from uri_input
    def _on_eos(self, bus, message):
        if self.data.loop:
            playbin = self.get_pipeline()
            playbin.seek_simple(Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT, 0)
            playbin.set_state(Gst.State.PLAYING)
        else:
            super()._on_eos(bus, message)

    def on_element_setup(self, playbin, element):
        factory = element.get_factory()
        if factory:
            name = factory.get_name()
            if name == "urisourcebin":
                element.connect('pad-added', self.on_pad_added)

    def on_pad_added(self, urisourcebin, pad):
        caps = pad.query_caps()
        if caps:
            structure = caps.get_structure(0)
            if structure and structure.get_name().startswith('video/'):
                width = structure.get_int('width')[1]
                height = structure.get_int('height')[1]
                if width and height:
                    self.data.width = width
                    self.data.height = height

    def extract_video_url(self, youtube_url):
        ydl_opts = {
            'format': 'best',  # @TODO make selectable
            'quiet': True,
            'no_warnings': True,
            'force_generic_extractor': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=False)
                video_url = info_dict.get("url", None)
                return video_url
        except yt_dlp.utils.DownloadError:
            logger.log(f"Unsupported URL: {youtube_url}", level='DEBUG')
            return None


    def describe(self):

        return self.data



