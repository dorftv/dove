from pipelines.base import Pipeline
from models import input

class HLSMonitorPipeline(Pipeline):
    def __init__(self, src: str, src_name: str, width: int, height: int):
        self.src = src
        self.src_name = src_name
        self.width = width
        self.height = height

    def describe(self) -> input.Description:
        return input.Description(uid=self.uid)

    def get_pipeline_str(self):
        return f"interpipesink listen-to={self.src} ! video/x-raw,width={self.width},height={self.height} !\
               videoconvert ! queue ! x264enc ! mpegtsmux !\
               hlssink max-files=5 location=/var/dove/hls/{self.src_name}/segments/segment%%05d.ts playlist-location=/var/dove/hls/{self.src_name}/index.m3u8"
