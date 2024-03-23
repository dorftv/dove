from api.inputs_dtos import UriInputDTO
from .input import Input
from gi.repository import Gst, GLib
from logger import logger

from pipelines.description import Description
from pipelines.inputs.input import Input
import asyncio


class UriInput(Input):
    data: UriInputDTO

    def build(self):
        videosink_bin = Gst.parse_bin_from_description(f"{self.get_video_end()}", True)
        audiosink_bin = Gst.parse_bin_from_description(self.get_audio_end(), True)
        playbin = Gst.ElementFactory.make("playbin3", "playbin")
        playbin.set_name("playbin")
        playbin.set_property("uri", f"{ self.data.uri }")
        playbin.set_property("instant-uri", True)
        playbin.set_property("video-sink", videosink_bin)
        playbin.set_property("audio-sink", audiosink_bin)
        # @TODO add config option for buffer
        playbin.set_property('buffer-duration', 3 * Gst.SECOND)
        playbin.connect('element-setup', self.on_element_setup)

        self.add_pipeline(playbin)

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

    def describe(self):

        return self.data
