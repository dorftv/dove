from abc import ABC
from uuid import UUID, uuid4

from api.outputs_dtos import previewHlsOutputDTO
from caps import Caps
from pipelines.base import GSTBase
from pipelines.outputs.preview_hls_output import previewHlsOutput
from typing import Union
from api.inputs_dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO
import asyncio

from api.websockets import manager

class Input(GSTBase, ABC):
    data: InputDTO
    def get_video_end(self) -> str:
        return f" interpipesink name=video_{self.data.uid} async=true sync=true"

    def get_audio_end(self):
        return f" audioconvert ! volume name=volume volume={self.data.volume} ! queue ! interpipesink name=audio_{self.data.uid} async=true sync=true"
    def describe(self):

        return self
    
    def add_preview(self, handler, uid, src):
        output = previewHlsOutput(uid=uid, src=src, data=previewHlsOutputDTO(src=src))
        handler.add_pipeline(output)
        return uid

    def remove_preview(self, handler, uid):
        handler.delete_pipeline("outputs", uid)

    # for now we only have volume to update
    async def update(self, data):
        self.data.volume = data['volume']
        pipeline = self.get_pipeline()
        volume = pipeline.get_by_name('volume')
        volume.set_property('volume', data['volume'])
        await manager.broadcast("UPDATE", self.data)
