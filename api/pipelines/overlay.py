from pipelines.base import Pipeline
from models import input


class CompositorPipeline(Pipeline):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        super().__init__()
        
    def describe(self) -> input.Description:
        return input.Description(uid=self.uid)

    def get_pipeline_str(self):
        return f"compositor name=overlay src::alpha=1 bg::alpha=1 htmloverlay::alpha=1 ! \
        video/x-raw,width={self.width},height={self.height},format=BGRA,framerate=25/1 ! videorate ! videoconvert ! videoscale !\
        queue ! interpipesink name=finalsink  async=false sync=true"

class VideoPipeline(Pipeline):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        super().__init__()

    def get_pipeline_str(self):
        return f" videotestsrc name=bg ! video/x-raw,width={self.width},height={self.height},format=BGRA,framerate=25/1 ! videorate ! videoconvert ! videoscale ! queue ! overlay. "

class InterpipePipeline(Pipeline):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        super().__init__()

    def get_pipeline_str(self):
        return f" interpipesrc listen-to='' name=src format=time allow-renegotiation=true  is-live=true  do-timestamp=true  !  video/x-raw,width={self.width},height={self.height},framerate=25/1, ! videorate ! videoscale ! videoconvert ! queue ! overlay.  "

class WPEPipeline(Pipeline):
    def __init__(self, url):
        self.initial_url = url
        super().__init__()

    def get_pipeline_str(self):
        return f"wpesrc location={ self.initial_url }  draw-background=false  name=htmloverlay ! video/x-raw,format=BGRA  ! videoconvert ! queue ! overlay. "
