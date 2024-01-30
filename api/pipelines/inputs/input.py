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

from api.outputs_dtos import previewHlsOutputDTO
from pipeline_handler import HandlerSingleton



class Input(GSTBase, ABC):
    data: InputDTO
    def get_video_end(self) -> str:
        return f" interpipesink name=video_{self.data.uid} async=true sync=true"

    def get_audio_end(self):
        return f" audioconvert ! volume name=volume volume={self.data.volume} ! queue ! interpipesink name=audio_{self.data.uid} async=true sync=true"
    
    def add_preview(self):
        handler = HandlerSingleton()
        if not handler.get_preview_pipeline(self.data.uid) and self.data.enable_preview:
            output = previewHlsOutput(data=previewHlsOutputDTO(src=self.data.uid))
            handler.add_pipeline(output)
            asyncio.run(manager.broadcast("CREATE", output.data))

    async def update(self, data):
        self.data.volume = data['volume']
        pipeline = self.get_pipeline()
        volume = pipeline.get_by_name('volume')
        volume.set_property('volume', data['volume'])
        await manager.broadcast("UPDATE", self.data)

    def describe(self):

        return self

