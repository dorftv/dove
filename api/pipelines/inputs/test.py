from models.input import InputTypes
from pipelines.base import Pipeline
from models import input

class TestPipeline(Pipeline):
    pipeline_str: str = "v4l2src device=/dev/video0 ! videoconvert ! videoscale ! video/x-raw,width=320,height=240 ! theoraenc ! oggmux ! tcpserversink host=127.0.0.1 port=8080"

    def describe(self) -> "input.InputCreateDTO":
        return input.InputCreateDTO(
            uid=self.uid,
            type=InputTypes.test_src,
            name=self.name,
            state=self.state,
            height=self.height,
            width=self.width,
            preview=self.preview
        )