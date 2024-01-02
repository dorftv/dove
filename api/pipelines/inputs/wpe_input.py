from api.inputs_dtos import WpeInputDTO
from .input import Input

from pipelines.description import Description
from pipelines.inputs.input import Input


class WpeInput(Input):
    data: WpeInputDTO

    def build(self):
        pipeline_str = f" wpesrc location={self.data.location} draw-background={self.data.draw_background} name=wpesrc wpesrc. ! videoscale ! videorate ! videoconvert !  video/x-raw,width={self.data.width},height={self.data.height},format=BGRA,framerate=25/1 !  videoconvert ! videoscale ! videorate  !  " + self.get_video_end()
        audio_pipeline_str = f"  audiotestsrc volume=0 ! audioconvert ! audio/x-raw ! " + self.get_audio_end()
        pipeline_str += audio_pipeline_str

        self.add_pipeline(pipeline_str)

    def describe(self):

        return self.data

