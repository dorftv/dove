from pathlib import Path
from typing import Optional

from pipelines.outputs.output import Output
from api.outputs_dtos import previewHlsOutputDTO


class previewHlsOutput(Output):
    data: previewHlsOutputDTO
    output_base: Optional[Path] = Path("/var/dove/hls")

    def build(self):
        preview_path = self.output_base.joinpath(str(self.data.src))
        if not preview_path.is_dir():
            preview_path.mkdir(parents=True, exist_ok=False)


        self.add_pipeline(self.get_video_start() + f" videoconvert ! videoscale ! video/x-raw,format=I420 ! "
        f" x264enc  speed-preset=ultrafast ! video/x-h264,profile=main ! queue ! mpegtsmux ! "
        f" hlssink async-handling=true target-duration=1  max-files=5 "
        f" playlist-location={preview_path.joinpath('index.m3u8')} location={preview_path.joinpath('segment%05d.ts')} ")

    def describe(self):
        return self.data

        #self.add_pipeline(self.get_video_start() + f" videoconvert ! video/x-raw,format=I420 ! x264enc ! video/x-h264,profile=main ! queue ! mpegtsmux ! "
        #f"hlssink async-handling=true target-duration=3  max-files=5 playlist-location={preview_path.joinpath('index.m3u8')} "
        #f"location={preview_path.joinpath('segment%05d.ts')} ")