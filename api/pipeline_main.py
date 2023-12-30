from pipeline_handler import PipelineHandler
from startup import createElements

elements = createElements()
pipes = elements.create_mixer()
pipelines = PipelineHandler(pipes)
