from abc import ABC
from uuid import UUID
from api.dtos import InputDTO


from caps import Caps
from pipelines.base import GSTBase


class Input(GSTBase, ABC):
    uid: UUID
    def get_video_end(self) -> str:
        return f" {self.caps.video} ! queue ! interpipesink name=video_{self.uid} async=false sync=true"

    def get_audio_end(self):
        return f" {self.caps.audio} ! queue ! interpipesink name=audio_{self.uid} async=false sync=true"
    def describe(self):

        return self
