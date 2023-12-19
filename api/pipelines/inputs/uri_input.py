from api.dtos import InputDTO
from pipelines.description import Description
from pipelines.inputs.input import Input


class URIInput(Input):
    attrs: InputDTO

    def build(self):
        video_pipeline_str = f" uridecodebin3 uri={self.attrs.uri} name=uridecodebin_{self.uid} instant-uri=true uridecodebin_{self.uid}. ! " + self.get_video_end()
        audio_pipeline_str = f" uridecodebin_{self.uid}. ! " + self.get_audio_end()

        self.add_pipeline(video_pipeline_str + audio_pipeline_str)

    def describe(self):
        attrs = {
            "uri": self.uri
        }
        return Description(uid=self.uid, attrs=attrs)