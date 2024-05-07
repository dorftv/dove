from abc import ABC
from uuid import UUID, uuid4

from api.outputs_dtos import previewHlsOutputDTO
from caps import Caps
from pipelines.base import GSTBase
from pipelines.outputs.preview_hls_output import previewHlsOutput
from typing import Union
from api.inputs_dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO, updateInputDTO
import asyncio
from gi.repository import Gst, GLib

from api.websockets import manager
import time
from api.outputs_dtos import previewHlsOutputDTO
from pipeline_handler import HandlerSingleton



class Input(GSTBase, ABC):
    data: InputDTO
    def get_video_end(self) -> str:
        return f"  videorate ! videoconvert ! videoscale !  {self.get_caps('video') } ! queue  max-size-time=300000000 !  interpipesink name=video_{self.data.uid} async=true sync=true "

    def get_audio_end(self):
        return f" volume name=volume volume={self.data.volume} ! audioconvert ! audiorate ! audioresample ! { self.get_caps('audio') }  !  queue max-size-time=300000000 ! interpipesink name=audio_{self.data.uid} async=true sync=true "

    def add_preview(self):
        if self.data.preview == True:
            handler = HandlerSingleton()
            if not handler.get_preview_pipeline(self.data.uid):
                output = previewHlsOutput(data=previewHlsOutputDTO(src=self.data.uid))
                handler.add_pipeline(output)
                asyncio.run(manager.broadcast("CREATE", output.data))

    def seek_to_position(self, position):
        position_nanoseconds = position * Gst.SECOND
        playbin = self.get_pipeline()
        seek_event = Gst.Event.new_seek(1.0, Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                        Gst.SeekType.SET, position_nanoseconds,
                                        Gst.SeekType.NONE, 0)

        if playbin.send_event(seek_event):
            print(f"Seeked to position: {position} seconds")
        else:
            print("Seek failed!")

    async def update(self, data):
        pipeline = self.get_pipeline()
        if not isinstance(data, updateInputDTO):
            data = updateInputDTO.parse_obj(data)
        if data.volume is not None:
            self.data.volume = data.volume
            volume = pipeline.get_by_name('volume')
            volume.set_property('volume', data.volume)
        if data.state is not None:
            state_map = {
                'PLAYING': Gst.State.PLAYING,
                'PAUSED': Gst.State.PAUSED
            }
            pipeline.set_state(state_map[data.state])
        if data.position is not None:
            self.seek_to_position(data.position)
            self.data.position = data.position
            # @TODO fix preview after seeking when state=paused
            #if self.data.state == "PAUSED":


        await manager.broadcast("UPDATE", self.data)

    def describe(self):

        return self

