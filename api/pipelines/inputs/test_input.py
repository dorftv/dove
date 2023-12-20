from api.dtos import InputDTO, TestInputDTO
from .input import Input
from gi.repository import Gst
from pipelines.description import Description
from typing import Annotated, Optional


class TestInput(Input):
    
    pattern: int
    volume: Optional[float]
    wave: Optional[int] = 1
    freq: Optional[float] = 440.0

    def build(self):
        video_pipeline_str = f" videotestsrc is_live=true pattern={self.pattern}  name=videotestsrc_{self.uid} !" + self.get_video_end()
        audio_pipeline_str = f" audiotestsrc is-live=true wave={self.wave} freq={self.freq}  volume={self.volume} name=audiotestsrc_{self.uid} ! audioresample ! audioconvert !" + self.get_audio_end()
        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self, dto: TestInputDTO):
        self.pattern = dto.pattern
        self.wave = dto.wave
        self.freq = dto.freq
        return self
