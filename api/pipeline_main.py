
# elements = createElements()
# pipes = elements.create_mixer()
# pipelines = PipelineHandler(pipes)

pipelines = None
def get_pipeline_handler():
    from pipeline_handler import PipelineHandler
    from startup import createElements

    global pipelines

    if pipelines is None:
        print("None!!")
        elements = createElements()
        pipes = elements.create_mixer()
        pipelines = PipelineHandler(pipes)
    else:
        print("not none")

    return pipelines
