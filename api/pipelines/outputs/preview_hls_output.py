from pathlib import Path
from typing import Optional

from pipelines.outputs.output import Output
from api.outputs_dtos import previewHlsOutputDTO


class previewHlsOutput(Output):
    data: previewHlsOutputDTO
    output_base: Optional[Path] = Path("/var/dove/hls")

    def build(self):
        preview_path = self.output_base.joinpath(self.data.src.hex)
        if not preview_path.is_dir():
            preview_path.mkdir(parents=True, exist_ok=False)

        # @TODO get from config
        width = 320
        height = 180
        self.add_pipeline(self.get_video_start() + f" videoconvert ! video/x-raw,format=I420,width={width},height={height} ! "
        f" x264enc ! video/x-h264,profile=main ! queue ! mpegtsmux ! "
        f" hlssink async-handling=true target-duration=3  max-files=5 "
        f" playlist-location={preview_path.joinpath('index.m3u8')} location={preview_path.joinpath('segment%05d.ts')} ")

    def describe(self):
        return self.data
