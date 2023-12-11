from pipelines.base import Pipeline
from models import input


class FinalPipeline(Pipeline):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        super().__init__()

    def describe(self) -> input.Description:
        return input.Description(uid=self.uid)

    def get_pipeline_str(self):
        return f"interpipesrc listen-to=finalsink allow-renegotiation=false format=time ! video/x-raw,width={self.width},height={self.height} ! videoconvert ! queue ! theoraenc ! oggmux ! tcpserversink host=127.0.0.1 port=8080"
