from pipelines.base import Pipeline
from gi.repository import GLib


class PipelineHandler:
    pipelines: list[Pipeline]

    def __init__(self):
        self.pipelines = []

    def add_pipeline(self, pipeline: Pipeline):
        self.pipelines.append(pipeline)
    
    def start(self, set_all_playing=True):
        if set_all_playing:
            for pipeline in self.pipelines:
                pipeline.play()
        
        loop = GLib.MainLoop()
        loop.run()