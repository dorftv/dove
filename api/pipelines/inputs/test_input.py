from api.dtos import TestInputDTO
from .input import Input
from gi.repository import Gst
from pipelines.description import Description


class TestInput(Input):
    data: TestInputDTO

    def build(self):
        video_pipeline_str = f" videotestsrc is_live=true pattern={self.data.pattern}  name=videotestsrc_{self.uid} !" + self.get_video_end()
        audio_pipeline_str = f" audiotestsrc is-live=true wave={self.data.wave} freq={self.data.freq}  volume={self.data.volume} name=audiotestsrc_{self.uid} ! audioresample ! audioconvert !" + self.get_audio_end()
        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self):

        return self.data
        
