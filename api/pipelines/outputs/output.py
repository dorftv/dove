from abc import ABC
from uuid import UUID

from caps import Caps
from pipelines.base import GSTBase

class Output(GSTBase, ABC):
    uid: UUID
    src: UUID
    def get_video_start(self) -> str:
        return f" interpipesrc name=video_{self.uid} listen-to=video_{self.src} is-live=true format=time allow-renegotiation=false  stream-sync=restart-ts ! queue !  "

    def get_audio_start(self):
        return f" interpipesrc name=audio_{self.uid} listen-to=audio_{self.src} is-live=true format=time allow-renegotiation=false is-live=true stream-sync=restart-ts stream-sync=restart-ts ! queue ! "

    def describe(self):
        return self

                