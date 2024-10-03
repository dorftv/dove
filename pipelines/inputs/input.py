from abc import ABC
from uuid import UUID, uuid4

from pipelines.base import GSTBase
from pipelines.outputs.hlssink2 import hlssink2Output
from api.outputs.hlssink2 import hlssink2OutputDTO
from api.outputs.srtsink import srtsinkOutputDTO
from pipelines.outputs.srtsink import srtsinkOutput

from typing import Union
from api.input_models import InputDTO, SuccessDTO, InputDeleteDTO, updateInputDTO
import asyncio
from gi.repository import Gst, GLib

from api.websockets import manager
import time
from pipeline_handler import HandlerSingleton
from config_handler import ConfigReader

import logging

logger = logging.getLogger(__name__)
config = ConfigReader()

class Input(GSTBase, ABC):
    data: InputDTO
    def get_video_end(self) -> str:
        return f"  videorate ! videoconvert ! videoscale !  {self.get_caps('video') } ! queue  max-size-time=300000000 ! interpipesink name=video_{self.data.uid} async=true sync=true "

    def get_audio_end(self):
        return f" volume name=volume volume={self.data.volume} ! audioconvert ! audiorate ! audioresample ! { self.get_caps('audio') }  !  queue max-size-time=300000000 ! interpipesink name=audio_{self.data.uid} async=true sync=true "

    def create_preview(self):
        self.create_preview_pipeline()

    def create_preview_pipeline(self):
        uid = self.data.uid
        if self.data.preview == True:
            handler = HandlerSingleton()
            preview = handler.get_preview_pipeline(uid)

            if  preview is None:
                if config.get_whep_proxy:
                    host =  config.get_whep_proxy('host')
                    ingest_port = config.get_whep_proxy('ingest_port')
                preview_config = config.get_preview_config('inputs')
                if preview_config['type'] == "hlssink2":
                    previewOutput = hlssink2Output(data=hlssink2OutputDTO(
                        src=uid,
                        is_preview=True,
                        ** preview_config
                    ))
                elif preview_config['type'] == "srtsink":
                    previewOutput = srtsinkOutput(data=srtsinkOutputDTO(
                        src=uid,
                        is_preview=True,
                         uri=f"srt://{host}:{ingest_port}?streamid=publish:{uid}&pkt_size=1316",
                        ** preview_config
                    ))
                elif preview_config['type'] == "rtspclientsink":
                    previewOutput = rtspclientsinkOutput(data=rtspclientsinkOutputDTO(
                        src=uid,
                        is_preview=True,
                        location=f"rtsp://{ host }:{ ingest_port }/{uid}",
                        ** preview_config
                    ))
                handler.add_pipeline(previewOutput)
                asyncio.run(manager.broadcast("CREATE", previewOutput.data))


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
        if data.loop is not None:
            self.data.loop = data.loop
        if data.volume is not None:
            self.data.volume = data.volume
            volume = pipeline.get_by_name('volume')
            volume.set_property('volume', data.volume)
        if data.state is not None:
            state_map = {
                'PLAYING': Gst.State.PLAYING,
                'PAUSED': Gst.State.PAUSED,
                'READY': Gst.State.READY,
                'NULL': Gst.State.NULL,

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

