from pathlib import Path
from typing import Optional
from uuid import UUID
from pipeline_handler import HandlerSingleton
from pipelines.outputs.output import Output
from api.outputs.hlssink2 import hlssink2OutputDTO
from gi.repository import Gst
from config_handler import ConfigReader

config = ConfigReader()


class hlssink2Output(Output):
    data: hlssink2OutputDTO
    output_base: Optional[Path] = Path(config.get_hls_path())

    def build(self):
        preview_path = self.output_base.joinpath(str(self.data.src))
        if not preview_path.is_dir():
            preview_path.mkdir(parents=True, exist_ok=False)

        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        pipeline_audio_str = ""

        if input.has_audio_or_video("audio"):
            audioenc = self.get_audio_encoder_pipeline(self.data.audio_encoder.name)
            pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! { audioenc } ! mux.audio"

        videoenc = self.get_video_encoder_pipeline(self.data.video_encoder.name)
        # @TODO Remove left overs from old preview output.
        self.add_pipeline(
            f"{self.get_video_start()}  videoconvert ! videoscale ! videorate ! { videoenc } ! "
            f""
            f"hlssink2 name=mux async-handling=true target-duration=1  playlist-length=3 max-files=3  "
            f""
            f"playlist-location={preview_path.joinpath('index.m3u8')} location={preview_path.joinpath('segment%05d.ts')} "
            f""
            f"{ pipeline_audio_str } ")




    def describe(self):
        return self.data
