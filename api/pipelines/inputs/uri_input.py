from api.inputs_dtos import UriInputDTO
from .input import Input
from gi.repository import Gst, GLib

from pipelines.description import Description
from pipelines.inputs.input import Input
import asyncio


class UriInput(Input):
    data: UriInputDTO

    def build(self):
        videosink_bin = Gst.parse_bin_from_description(self.get_video_end(), True)
        audiosink_bin = Gst.parse_bin_from_description(self.get_audio_end(), True)
        playbin = Gst.ElementFactory.make("playbin3", "playbin")
        playbin.set_property("uri", f"{ self.data.uri }")
        playbin.set_property("instant-uri", True)
        playbin.set_property("video-sink", videosink_bin)
        playbin.set_property("audio-sink", audiosink_bin)
        # @TODO add config option for buffer
        playbin.set_property('buffer-duration', 1 * Gst.SECOND)
        playbin.connect('about-to-finish', lambda e : asyncio.run(self._on_about_to_finish(e)))

        self.add_pipeline(playbin)

    async def _on_about_to_finish(self, playbin):
        if self.data.loop:
            playbin.set_property("uri", playbin.get_property('uri'))

    def describe(self):

        return self.data
