from pathlib import Path
from typing import Optional
from logger import logger
import asyncio
from api.websockets import manager

from uuid import UUID, uuid4
from pipelines.mixers.mixer import Mixer
from api.mixers_dtos import sceneMixerDTO, mixerInputDTO, mixerCutDTO, mixerPadDTO
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
            f" audiotestsrc wave=4 ! { audio_caps } ! liveadder latency=50 name=audiomixer_{self.data.uid} force-live=true ignore-inactive-pads=true !  audioconvert ! audiorate ! audioresample ! { audio_caps } ! "
            + self.get_audio_end())

        loop = self.data.countMixerInputs()
        if loop is None:
            loop = self.data.n
        for i in range(loop):
            pad = self.add_pads() 

        # TODO update for api creation
        self.data.update_sources_with_defaults()


    async def update(self, data):
        sink = data.get('sink',None)
        if sink is not None:
            sink = data.pop('sink')
            uid = data.pop('uid')
            self.data.update_mixer_input(sink, **data)
            for audio_or_video in ["audio", "video"]:
                if 'src' in data:
                    if data.get('src') == "None":
                        self.unlink_pad(audio_or_video, sink)

                    else:
                        self.link_pad(audio_or_video, sink)
         
                pad = self.update_pad_from_sources(audio_or_video, sink)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))


    def remove_source(self, input):
        sink = input.sink
        if sink:       
            mixerInputDTO = self.data.getMixerInputDTO(input.sink)
        if mixerInputDTO:
            for audio_or_video in ["audio", "video"]:                 
                self.data.update_mixer_input(sink, src="None")
                self.update_pad_from_sources(audio_or_video, sink)                
                self.unlink_pad(audio_or_video, sink)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))

    def remove_pads(self, mixerSource: mixerInputDTO = None):
        if mixerSource is not None:

            sink = mixerSource.sink
            if sink:
                self.remove_mixer_pad("video", sink)
                self.remove_mixer_pad("audio", sink)
                self.data.removeInput(sink)
                asyncio.create_task(manager.broadcast("UPDATE", self.data))
            return
        
           

    def remove_mixer_pad(self, audio_or_video, sink_name):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)
        self.unlink_pad(audio_or_video, sink_name)
        sink_pad = self.get_mixer_pad(audio_or_video, sink_name)
        mixer.remove_pad(sink_pad)
        return

    def describe(self):
        return self.data
