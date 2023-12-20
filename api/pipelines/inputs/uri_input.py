from api.dtos import UriInputDTO
from .input import Input
from typing import Annotated, Optional

from pipelines.description import Description
from pipelines.inputs.input import Input


class URIInput(Input):
    uri: str
    # @TODO  how can we get out values from DTO
    #dto: UriInputDTO
    volume: Optional[float]
    #volume: float
    def build(self):
        video_pipeline_str = f" uridecodebin3 uri={self.uri} name=uridecodebin instant-uri=true uridecodebin. !" + self.get_video_end()
        audio_pipeline_str = f" uridecodebin. ! " + self.get_audio_end()

        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self, dto: UriInputDTO):
        #self.uri = dto.uri
        #self.volume = dto.volume

        return self
