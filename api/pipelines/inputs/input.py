from abc import ABC
from uuid import UUID, uuid4

from api.outputs_dtos import previewHlsOutputDTO
from caps import Caps
from pipelines.base import GSTBase
from pipelines.outputs.preview_hls_output import previewHlsOutput


class Input(GSTBase, ABC):
    uid: UUID
    def get_video_end(self) -> str:
        return f"  queue ! interpipesink name=video_{self.uid} async=true sync=true"

    def get_audio_end(self):
        return f" queue ! interpipesink name=audio_{self.uid} async=true sync=true"
    def describe(self):

        return self
    
    def add_preview(self, handler, uid, src):
        output = previewHlsOutput(uid=uid, src=src, data=previewHlsOutputDTO(src=src))
        handler.add_pipeline(output)
        return uid

    def remove_preview(self, handler, uid):
        handler.delete_pipeline("outputs", uid)