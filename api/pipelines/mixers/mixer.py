from pipelines.base import GSTBase
from uuid import UUID
from abc import ABC


class Mixer(GSTBase, ABC):
    uid: UUID
    listen_to: str = "videomixer_out"
    def get_pipeline_end(self):
        return f"" #interpipesrc listen_to={self.listen_to} name=output_{self.uid} format=time allow-renegotiation=true do-timestamp=true is-live=true ! queue ! "