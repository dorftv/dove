from pathlib import Path
from typing import Optional
import asyncio
from api.websockets import manager

from pipelines.mixers.mixer import Mixer
from api.mixers_dtos import programMixerDTO, mixerCutProgramDTO, mixerInputDTO, mixerCutDTO
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstController', '1.0')
from gi.repository import GObject, Gst, GstController
from time import sleep


class programMixer(Mixer):
    data: programMixerDTO

    def build(self):

        self.add_pipeline(f"videotestsrc is-live=true pattern=2 ! { self.get_caps('video') } ! "
            f" compositor  name=videomixer_{self.data.uid} background=black force-live=true ignore-inactive-pads=true sink_0::alpha=1 ! videorate ! videoconvert ! videoscale ! { self.get_caps('video') } !   "
            + self.get_video_end() +
            f" audiotestsrc wave=4 ! { self.get_caps('audio') } ! liveadder  latency=70 name=audiomixer_{self.data.uid} force-live=true  ignore-inactive-pads=true !   { self.get_caps('audio') } ! "
            + self.get_audio_end())
        # Pads for scene sources
        self.add_slot()
        self.add_slot()
        # @TODO add overays index >= 2

    def cut_program(self, data: mixerCutProgramDTO):
        if self.data.active == None:
            old_sink = None
            index = 0
        else:
            mixerInputDTO = self.data.getMixerInputDTO(self.data.active)
            old_sink = mixerInputDTO.sink
            index = 0 if self.data.active == 1 else 1


        self.data.update_mixer_input(index, src=data.src)
        self.data.active = index
        for audio_or_video in ["audio", "video"]:
            sink = self.add_mixer_pad(audio_or_video, index)
            if data.transition == "cut" or data.transition is None:
                self.link_pad(audio_or_video, index)
                if old_sink is not None:
                    self.unlink_pad(audio_or_video, old_sink)

        asyncio.create_task(manager.broadcast("UPDATE", self.data))
        return data

    # @TODO implement fade
    def get_alpha_controller(pad):
        cs = GstController.InterpolationControlSource()
        cs.set_property('mode', GstController.InterpolationMode.LINEAR)

        cb = GstController.DirectControlBinding.new(pad, 'alpha', cs)
        pad.add_control_binding(cb)
        return cs

    def describe(self):
        return self.data
