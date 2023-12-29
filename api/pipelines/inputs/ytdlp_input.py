from api.inputs_dtos import ytDlpInputDTO
from .input import Input

from pipelines.description import Description
from pipelines.inputs.input import Input
import json

import yt_dlp

class ytDlpInput(Input):
    data: ytDlpInputDTO

    def build(self):
        video_pipeline_str = f" uridecodebin3 uri={self.extract_video_url(self.data.uri)} name=uridecodebin instant-uri=true uridecodebin. ! " + self.get_video_end()
        audio_pipeline_str = f" uridecodebin. ! " + self.get_audio_end()

        self.add_pipeline(video_pipeline_str + audio_pipeline_str)


    def extract_video_url(self, youtube_url):
        ydl_opts = {
            'format': 'best',  # You can choose different formats as needed
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



