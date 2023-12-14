from pipelines.base import Pipeline
from gi.repository import GLib


class PipelineHandler:
    pipelines: dict[str, list[Pipeline]]

    def __init__(self):
        self.pipelines = {
            "inputs": [],
            "outputs": []
        }

    def add_pipeline(self, pipeline: Pipeline, type: str = "inputs"):
        if pipeline is not None:
            if type in self.pipelines:
                self.pipelines[type].append(pipeline)
            else:
                self.pipelines[type] = [pipeline]

    def delete_pipeline(self):

    def start(self, set_all_playing=True):
        if set_all_playing:
            for pipelines in self.pipelines.values():
                for pipeline in pipelines:
                    pipeline.play()

        loop = GLib.MainLoop()
        loop.run()
