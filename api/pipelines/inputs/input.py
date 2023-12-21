from abc import ABC
from uuid import UUID


from caps import Caps
from pipelines.base import GSTBase


class Input(GSTBase, ABC):
    uid: UUID
    def get_video_end(self) -> str:
        return f" queue ! interpipesink name=video_{self.uid} async=false sync=true"

    def get_audio_end(self):
        return f" queue ! interpipesink name=audio_{self.uid} async=false sync=true"
    def describe(self):

        return self
