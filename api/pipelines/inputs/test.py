from models.input import InputTypes
from pipelines.base import Pipeline
from models import input

class TestPipeline(Pipeline):
    def get_pipeline_str(self):
        return f"videotestsrc name=video_<uid> is-live=true ! videoconvert ! videoscale ! video/x-raw,width={self.width},height={self.height},pixel-aspect-ratio=1/1,format=RGBA !  interpipesink name=video_uid"

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