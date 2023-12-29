from api.inputs_dtos import WpeInputDTO
from .input import Input

from pipelines.description import Description
from pipelines.inputs.input import Input


class WpeInput(Input):
    data: WpeInputDTO

    def build(self):
        pipeline_str = f" wpesrc location=https://dorftv.at name=wpesrc wpesrc. ! videoscale ! videorate ! videoconvert !  video/x-raw,width=1280,height=720,framerate=25/1,format=BGRA,framerate=25/1 !  videoconvert ! videoscale ! videorate  !  " + self.get_video_end()
#        if self.has_audio_or_video("audio"):
#            audio_pipeline_str = f"  wpesrc. ! audioconvert ! audio/x-raw ! " + self.get_audio_end()
#            pipeline_str += audio_pipeline_str

        self.add_pipeline(pipeline_str)

    def describe(self):

        return self.data

