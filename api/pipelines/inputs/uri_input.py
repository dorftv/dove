from api.dtos import InputDTO
from pipelines.description import Description
from pipelines.inputs.input import Input


class URIInput(Input):
    attrs: InputDTO

    def build(self):
        video_pipeline_str = f"uridecodebin3 uri={self.attrs.uri} name=uridecodebin instant-uri=true uridecodebin. !" + self.get_video_end()
        audio_pipeline_str = f"uridecodebin. ! " + self.get_audio_end()

        self.add_pipeline(video_pipeline_str)
        self.add_pipeline(audio_pipeline_str)

    def describe(self):
        attrs = {
            "uri": self.uri
        }
        return Description(uid=self.uid, attrs=attrs)
