from abc import ABC
from uuid import UUID
from api.dtos import InputDTO


from caps import Caps
from pipelines.base import GSTBase
from typing import Annotated, Optional


class Input(GSTBase, ABC):
    uid: UUID
    def get_video_end(self) -> str:
        return f" {self.caps.video} ! queue ! interpipesink name=video_{self.uid} async=false sync=true"

    def get_audio_end(self):
        return f" {self.caps.audio} ! queue ! interpipesink name=audio_{self.uid} sync=true async=false"
    def describe(self, dto: InputDTO):
        self.uri = dto.uri
        self.volume = dto.volume
        return self
