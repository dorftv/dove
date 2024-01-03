
# elements = createElements()
# pipes = elements.create_mixer()
# pipelines = PipelineHandler(pipes)

pipelines = None
def get_pipeline_handler():
    from pipeline_handler import PipelineHandler
    from startup import createElements

    global pipelines

    if pipelines is None:
        elements = createElements()
        pipes = elements.create_mixer()
        pipelines = PipelineHandler(pipes)

    return pipelines

class HandlerSingleton:
    def __new__(cls):
        from pipeline_handler import PipelineHandler
        from startup import createElements

        if not hasattr(cls, 'handler'):
            elements = createElements()
            pipes = elements.create_mixer()
            cls.handler = PipelineHandler(pipes)

        return cls.handler
