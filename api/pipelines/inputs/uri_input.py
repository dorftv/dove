from api.dtos import UriInputDTO
from .input import Input
from typing import Annotated, Optional

from pipelines.description import Description
from pipelines.inputs.input import Input


class URIInput(Input):
    dto: UriInputDTO

    def build(self):
        video_pipeline_str = f" uridecodebin3 uri={self.dto.uri} name=uridecodebin instant-uri=true uridecodebin. !" + self.get_video_end()
        audio_pipeline_str = f" uridecodebin. ! " + self.get_audio_end()

        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self, dto: UriInputDTO):
    

        return self
