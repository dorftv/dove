from pipelines.base import GSTBase


class Output(GSTBase):
    listen_to: str = "videomixer_out"
    def get_pipeline_start(self):
        return f"interpipesrc listen_to={self.listen_to} name=output_{self.uid} format=time allow-renegotiation=true do-timestamp=true is-live=true ! queue ! "