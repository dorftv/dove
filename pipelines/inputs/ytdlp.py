from api.inputs.ytdlp import YtdlpInputDTO
from .input import Input
from gi.repository import Gst, GLib
from logger import logger

from pipelines.description import Description
from pipelines.inputs.input import Input
import json
import logging

logger = logging.getLogger(__name__)
import yt_dlp

class YtdlpInput(Input):
    data: YtdlpInputDTO

    def build(self):
        videosink_bin = Gst.parse_bin_from_description(f"{self.get_video_end()}", True)
        audiosink_bin = Gst.parse_bin_from_description(self.get_audio_end(), True)
        playbin = Gst.ElementFactory.make("playbin3", "playbin")
        playbin.set_name("playbin")
        url = self.extract_video_url(self.data.uri)
        if url:
            playbin.set_property("uri", url)

            # @TODO add config option for buffer
            playbin.set_property("buffer-size", 1048576  )
            playbin.set_property("async-handling", True)
            playbin.set_property('buffer-duration', 1 * Gst.SECOND)

            playbin.set_property("video-sink", videosink_bin)
            playbin.set_property("audio-sink", audiosink_bin)

            playbin.connect('element-setup', self.on_element_setup)
            playbin.connect('about-to-finish', self._on_about_to_finish)
            self.add_pipeline(playbin)

    def _on_about_to_finish(self, playbin):
        if self.data.loop:
            playbin = self.get_pipeline()
            playbin.set_property("uri",  playbin.get_property("uri"))

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
            'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            'format_sort': ['res:1080', 'ext:mp4:m4a'],
            'quiet': True,
            'no_warnings': True,
            'force_generic_extractor': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(youtube_url, download=False)

                # Get the best format
                formats = info_dict.get('formats', [info_dict])
                best_format = next((f for f in reversed(formats) if f.get('acodec') != 'none' and f.get('vcodec') != 'none'), None)

                if best_format:
                    video_url = best_format['url']
                    format_id = best_format['format_id']
                    extension = best_format['ext']
                    resolution = best_format.get('resolution', 'N/A')
                    fps = best_format.get('fps', 'N/A')
                    vcodec = best_format.get('vcodec', 'N/A')
                    acodec = best_format.get('acodec', 'N/A')
                    return video_url
                else:
                    return None

        except yt_dlp.utils.DownloadError:
            logger.log(f"Unsupported URL: {youtube_url}", level='DEBUG')
            return None

    def describe(self):

        return self.data



