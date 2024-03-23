from pathlib import Path
from typing import Optional
from uuid import UUID
from pipeline_handler import HandlerSingleton
from pipelines.outputs.output import Output
from api.outputs_dtos import previewHlsOutputDTO
from gi.repository import Gst


class previewHlsOutput(Output):
    data: previewHlsOutputDTO
    output_base: Optional[Path] = Path("/var/dove/hls")

    def build(self):
        preview_path = self.output_base.joinpath(str(self.data.src))
        if not preview_path.is_dir():
            preview_path.mkdir(parents=True, exist_ok=False)
        
        handler = HandlerSingleton()
        input = handler.getpipeline(self.data.src)
        pipeline_audio_str = ""

        if input.has_audio_or_video("audio"):
                pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! voaacenc  ! aacparse !  queue ! mux."


        self.add_pipeline(self.get_video_start() + f" videoconvert ! videoscale ! videorate ! "
         + self.get_encoder_string() + 
        f" mpegtsmux name=mux ! hlssink async-handling=true target-duration=1  playlist-length=3 max-files=3  "
        f" playlist-location={preview_path.joinpath('index.m3u8')} location={preview_path.joinpath('segment%05d.ts')} "
        f" { pipeline_audio_str }")

    def get_encoder_string(self):
        video_caps = f"video/x-raw,width={self.data.width},height={self.data.height}"

        vaapitest = Gst.ElementFactory.make("vah264enc", "vaapitest")
        if vaapitest is not None:
            return f"{video_caps} ! vapostproc ! vah264enc  ! video/x-h264,profile=high ! h264parse ! "
        else:
            return f"{video_caps} ! x264enc  speed-preset=ultrafast ! video/x-h264,profile=baseline ! "

        

    def describe(self):
        return self.data
