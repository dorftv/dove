from abc import ABC
from uuid import UUID

from api.output_models import OutputDTO

from pipelines.base import GSTBase


class Output(GSTBase, ABC):
    data: OutputDTO
    def get_video_start(self) -> str:
        return f" interpipesrc name=video_{self.data.uid} listen-to=video_{self.data.src} is-live=true format=time allow-renegotiation=true stream-sync=restart-ts leaky-type=downstream ! "
    def get_audio_start(self):
        return f" interpipesrc name=audio_{self.data.uid} listen-to=audio_{self.data.src} is-live=true format=time allow-renegotiation=true stream-sync=restart-ts leaky-type=downstream ! "

    def describe(self):
        return self

