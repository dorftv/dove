from dove.pipelines.outputs.output import Output
from dove.api.outputs.rtspclientsink import rtspclientsinkOutputDTO


class rtspclientsinkOutput(Output):
    data: rtspclientsinkOutputDTO

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid

        video_str = (
            f" rtspclientsink name=sink_{uid} location={self.data.location} "
            f" {self.get_video_start(dynamic)} sink_{uid}.sink_0 "
        )

        audio_str = (
            f" {self.get_audio_start(dynamic)} sink_{uid}.sink_1 "
        )

        return video_str + audio_str
