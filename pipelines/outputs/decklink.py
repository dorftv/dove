
from pathlib import Path
from typing import Optional
from pipeline_handler import HandlerSingleton

from pipelines.outputs.output import Output
from api.outputs.decklink import DecklinkOutputDTO


class DecklinkOutput(Output):
    data: DecklinkOutputDTO

    def build(self):
        pipeline_audio_str = ""
        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        if input.has_audio_or_video("audio"):
                pipeline_audio_str = f" {self.get_audio_start()}  audioresample ! audioconvert  ! queue !   decklinkaudiosink device-number={self.data.device} sync=true"

        interlace_str = "videoconvert ! interlace field-pattern=2:2 ! queue ! " if self.data.interlaced else ""

        self.add_pipeline(self.get_video_start() + f" {interlace_str}  videorate !  videoconvert ! videoscale ! video/x-raw,format=UYVY ! queue !  "
            f" decklinkvideosink device-number={self.data.device} async=true  mode={self.data.mode} sync=true "
            f" { pipeline_audio_str }")


    def describe(self):
        return self.data


