from abc import ABC
from uuid import UUID

from pipelines.base import GSTBase


class Input(GSTBase, ABC):
    uid: UUID
    video_caps: str
    audio_caps: str

    def get_video_end(self) -> str:
        return f" {self.video_caps} ! queue ! interpipesink name=video_{self.uid} async=false sync=true"

    def get_audio_end(self):
        return f" audioresample ! audioconvert ! {self.audio_caps} ! queue ! interpipesink name=audio_input1 sync=true async=false"
