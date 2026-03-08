from pipelines.outputs.output import Output
from api.outputs.shout2send import Shout2sendOutputDTO


class Shout2sendOutput(Output):
    data: Shout2sendOutputDTO

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid

        audio_str = (
            f" {self.get_audio_start(dynamic)} "
            f" shout2send name=sink_{uid} "
            f" mount={self.data.mount} port={self.data.port} "
            f" username={self.data.username} password={self.data.password} "
            f" ip={self.data.ip} sync=false "
        )

        return audio_str
