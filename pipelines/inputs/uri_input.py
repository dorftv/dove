from api.inputs_dtos import UriInputDTO
from .input import Input
from gi.repository import Gst, GLib

from pipelines.description import Description
from pipelines.inputs.input import Input
import asyncio


class UriInput(Input):
    data: UriInputDTO

    def build(self):
        videosink_bin = Gst.parse_bin_from_description(f"videoconvert ! video/x-raw,format=BGRA ! queue ! {self.get_video_end()}", True)
        audiosink_bin = Gst.parse_bin_from_description(self.get_audio_end(), True)
        playbin = Gst.ElementFactory.make("playbin3", "playbin")
        playbin.set_name("playbin")
        playbin.set_property("uri", f"{ self.data.uri }")
        playbin.set_property("instant-uri", True)
        playbin.set_property("video-sink", videosink_bin)
        playbin.set_property("audio-sink", audiosink_bin)
        # @TODO add config option for buffer
        playbin.set_property('buffer-duration', 1 * Gst.SECOND)
        # use EOS for now. about-to-finish is emitted to soon
        #playbin.connect('about-to-finish', lambda e : asyncio.run(self._on_about_to_finish(e)))

        self.add_pipeline(playbin)

    def _on_eos(self, bus, message):
        if self.data.loop:
            playbin = self.get_pipeline()
            playbin.set_property("uri", playbin.get_property('uri'))
            playbin.set_state(Gst.State.PLAYING)
        else:
            super()._on_eos(bus, message)


    def describe(self):

        return self.data
