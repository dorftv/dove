from api.inputs_dtos import UriInputDTO
from .input import Input

from pipelines.description import Description
from pipelines.inputs.input import Input


class URIInput(Input):
    data: UriInputDTO

    def build(self):
        video_pipeline_str = f" uridecodebin3 uri={self.data.uri} name=uridecodebin instant-uri=true uridecodebin. !" + self.get_video_end()
        audio_pipeline_str = f" uridecodebin. ! " + self.get_audio_end()

        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self):

        return self.data
