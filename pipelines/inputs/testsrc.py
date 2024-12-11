from api.inputs.testsrc import TestsrcInputDTO
from .input import Input
from gi.repository import Gst
from pipelines.description import Description


class TestsrcInput(Input):
    data: TestsrcInputDTO

    def build(self):
        video_pipeline_str = f" videotestsrc do-timestamp=true is_live=true pattern={self.data.pattern}  name=videotestsrc_{self.data.uid}  !  {self.get_caps('video') } ! "  + self.get_video_end()
        audio_pipeline_str = f" audiotestsrc do-timestamp=true is-live=true wave={self.data.wave} freq={self.data.freq}  volume={self.data.volume} name=audiotestsrc_{self.data.uid} ! { self.get_caps('audio') } ! " + self.get_audio_end()
        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self):

        return self.data

