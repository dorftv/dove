from pathlib import Path
from typing import Optional
from logger import logger
import asyncio
from api.websockets import manager

from uuid import UUID, uuid4
from pipelines.mixers.mixer import Mixer
from api.mixers_dtos import sceneMixerDTO, mixerInputDTO, mixerCutDTO, mixerSlotDTO
from gi.repository import Gst, GLib


class sceneMixer(Mixer):
    data: sceneMixerDTO


    def build(self):
        # @TODO improve caps handling
        caps = f"video/x-raw,width={self.data.width},height={self.data.height},format=BGRA"
        audio_caps = "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2"

        self.add_pipeline(f"videotestsrc is-live=true pattern=18 ! {caps} ! "
            f" compositor zero-size-is-unscaled=false background=black force-live=true ignore-inactive-pads=true name=videomixer_{self.data.uid} sink_0::alpha=1 ! videoconvert ! videoscale ! videorate ! { caps } ! "
            f" {self.get_video_end()} "
            f" audiotestsrc wave=4 ! { audio_caps } ! liveadder   name=audiomixer_{self.data.uid} force-live=true ignore-inactive-pads=true !  audioconvert ! audiorate ! audioresample ! { audio_caps } ! "
            + self.get_audio_end())

        loop = self.data.countMixerInputs()
        if loop is None:
            loop = self.data.n
        for i in range(loop):
            # TODO update for api creation
            pad = self.add_slot()



    async def update(self, data):
        index = data.get('index',None)
        if index is not None:
            index = data.pop('index')
            uid = data.pop('uid')
            source = self.data.getMixerInputDTO(index)
            old_sink = source.sink

            self.data.update_mixer_input(index, **data)
            for audio_or_video in ["audio", "video"]:
                if 'src' in data:
                    if data.get('src') == "None":
                        self.unlink_pad(audio_or_video, old_sink)
                    else:
                        sink = self.add_mixer_pad(audio_or_video, index)
                        self.link_pad(audio_or_video, index)

                        if old_sink is not None:
                            self.unlink_pad(audio_or_video, old_sink)

            self.update_pad_from_sources(audio_or_video, index)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))



    def describe(self):
        return self.data
