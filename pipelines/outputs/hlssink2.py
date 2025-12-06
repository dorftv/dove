from pathlib import Path
from typing import Optional

from pipelines.outputs.output import Output
from api.outputs.hlssink2 import hlssink2OutputDTO
from config_handler import ConfigReader

config = ConfigReader()


class hlssink2Output(Output):
    data: hlssink2OutputDTO
    output_base: Optional[Path] = Path(config.get_hls_path())

    def build_pipeline_str(self, dynamic=False) -> str:
        # Determine preview path from src or encoder source
        src = self.data.src
        if not src and self.data.video_encoder:
            # Derive from encoder entity
            from pipeline_handler import HandlerSingleton
            handler = HandlerSingleton()
            enc = handler.get_pipeline("encoders", self.data.video_encoder)
            if enc:
                src = enc.data.src

        preview_path = self.output_base.joinpath(str(src or self.data.uid))
        preview_path.mkdir(parents=True, exist_ok=True)

        uid = self.data.uid

        video_str = (
            f" hlssink2 name=mux_{uid} async-handling=true target-duration=1 playlist-length=3 max-files=3 "
            f" playlist-location={preview_path.joinpath('index.m3u8')} location={preview_path.joinpath('segment%05d.ts')} "
            f" {self.get_video_start(dynamic)} mux_{uid}.video "
        )

        audio_str = (
            f" {self.get_audio_start(dynamic)} mux_{uid}.audio "
        )

        return video_str + audio_str
