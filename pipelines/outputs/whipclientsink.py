from pipelines.outputs.output import Output
from api.outputs.whipclientsink import whipclientsinkOutputDTO


class whipclientsinkOutput(Output):
    data: whipclientsinkOutputDTO

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid

        video_str = (
            f" {self.get_video_start(dynamic)} "
            f" whipclientsink name=sink_{uid} async-handling=true "
            f" signaller::whip-endpoint={self.data.whip_endpoint} "
        )

        return video_str
