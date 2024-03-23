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


class programMixer(Mixer):
    data: programMixerDTO
    
    def build(self):
        # @TODO improve caps handling
        caps = f"video/x-raw,width={self.data.width},height={self.data.height},format=BGRA"
        audio_caps = "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2"

        self.add_pipeline(f"videotestsrc pattern=2 is-live=true ! { caps } ! "
            f" compositor zero-size-is-unscaled=false background=black force-live=true  name=videomixer_{self.data.uid} sink_0::alpha=1 ! videoconvert ! videoscale ! videorate ! { caps } !  "
            + self.get_video_end() +
            f" audiotestsrc wave=4 ! { audio_caps } ! liveadder name=audiomixer_{self.data.uid}  ! audioconvert ! audiorate ! audioresample ! { audio_caps } ! "
            + self.get_audio_end())

        # Pads for scene sources
        self.add_pads()
        self.add_pads()
        # @TODO add overays

    def cut_program(self, data: mixerCutProgramDTO):
        print(data.src)
        if self.data.active == "sink_1" or self.data.active is None:
            self.set_input("sink_1", "sink_2", data)
        elif self.data.active == "sink_2":
            self.set_input("sink_2", "sink_1", data)

    def set_input(self, old_sink, new_sink, data):
        self.data.update_mixer_input(new_sink, src=data.src)
        self.data.active = new_sink
        for audio_or_video in ["audio", "video"]:
            bin = self.create_source_element(audio_or_video, new_sink)
            src_pad = bin.get_static_pad("src")

            self.set_pad_source(audio_or_video, new_sink)
            self.link_pad(audio_or_video, new_sink)

            if data.transition == "cut" or data.transition is None:
                self.data.update_mixer_input(new_sink, alpha=1)
                self.update_pad_from_sources(audio_or_video, new_sink)


                self.data.update_mixer_input(old_sink, src=None, alpha=0)
                self.update_pad_from_sources(audio_or_video, old_sink)
                self.unlink_pad(audio_or_video, old_sink)
        asyncio.create_task(manager.broadcast("UPDATE", self.data))

    def get_alpha_controller(pad):
        cs = GstController.InterpolationControlSource()
        cs.set_property('mode', GstController.InterpolationMode.LINEAR)

        cb = GstController.DirectControlBinding.new(pad, 'alpha', cs)
        pad.add_control_binding(cb)
        return cs

    def describe(self):
        return self.data
