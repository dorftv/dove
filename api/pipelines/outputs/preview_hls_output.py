from pathlib import Path
from typing import Optional

from pipeline_handler import HandlerSingleton
from pipelines.outputs.output import Output
from api.outputs_dtos import previewHlsOutputDTO


class previewHlsOutput(Output):
    data: previewHlsOutputDTO
    output_base: Optional[Path] = Path("/var/dove/hls")

    def build(self):
        preview_path = self.output_base.joinpath(str(self.data.src))
        if not preview_path.is_dir():
            preview_path.mkdir(parents=True, exist_ok=False)
        
        audio_caps = "audio/x-raw, format=S16LE, layout=(string)interleaved, rate=(int)44100, channels=(int)2"

        # @TODO get source element
        handler = HandlerSingleton()
        print("test", handler.get_pipelines("inputs"))
        pipeline_audio_str = ""
        if self.has_audio_or_video("audio"):
                pipeline_audio_str = f" {self.get_audio_start()}  audioconvert ! audioresample ! {audio_caps} ! voaacenc  ! aacparse !  queue ! mux."


        self.add_pipeline(self.get_video_start() + f" videoconvert ! videoscale ! videorate !  video/x-raw,width=320,height=180 ! queue  !  "
        f" x264enc  speed-preset=ultrafast ! video/x-h264,profile=baseline ! mpegtsmux name=mux ! "
        f" hlssink async-handling=true target-duration=1  max-files=3 "
        f" playlist-location={preview_path.joinpath('index.m3u8')} location={preview_path.joinpath('segment%05d.ts')} "
        f" { pipeline_audio_str }")

        
        

    def describe(self):
        return self.data
