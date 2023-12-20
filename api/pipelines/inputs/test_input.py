from api.dtos import InputDTO, TestInputDTO
from .input import Input
from gi.repository import Gst
from pipelines.description import Description
from typing import Annotated, Optional


class TestInput(Input):
    dto: TestInputDTO

    def build(self):
        video_pipeline_str = f" videotestsrc is_live=true pattern={self.dto.pattern}  name=videotestsrc_{self.uid} !" + self.get_video_end()
        audio_pipeline_str = f" audiotestsrc is-live=true wave={self.dto.wave} freq={self.dto.freq}  volume={self.dto.volume} name=audiotestsrc_{self.uid} ! audioresample ! audioconvert !" + self.get_audio_end()
        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self, dto: TestInputDTO):
        self.pattern = dto.pattern
        self.wave = dto.wave
        self.freq = dto.freq
        self.volume = dto.volume

        return self
        
