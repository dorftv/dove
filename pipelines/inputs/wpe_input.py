from api.inputs_dtos import WpeInputDTO
from .input import Input

from pipelines.description import Description
from pipelines.inputs.input import Input


class WpeInput(Input):
    data: WpeInputDTO

    def build(self):
        pipeline_str = f" wpesrc location={self.data.location} draw-background={self.data.draw_background} name=wpesrc wpesrc. ! videoconvert ! videoscale ! video/x-raw,width={self.data.width},height={self.data.height},format=BGRA  !  " + self.get_video_end()

        self.add_pipeline(pipeline_str)

    def describe(self):

        return self.data

