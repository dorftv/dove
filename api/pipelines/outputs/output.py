from abc import ABC
from uuid import UUID

from caps import Caps
from pipelines.base import GSTBase

class Output(GSTBase, ABC):
    uid: UUID
    src: UUID
    def get_video_start(self) -> str:
        return f" interpipesrc name=video_{self.uid} listen-to={self.src} "

    def get_audio_start(self):
        return f" interpipesrc name=audio_{self.uid} listen-to={self.src} "

    def describe(self):

        return self

                