from logger import logger
from api.mixers_dtos import mixerCutDTO, mixerInputsDTO, mixerInputDTO, mixerDTO
from pipelines.base import GSTBase
from abc import ABC
from gi.repository import Gst, GLib
from api.websockets import manager
import asyncio
from uuid import UUID, uuid4



class Mixer(GSTBase, ABC):

    data: mixerDTO
    
    def get_video_end(self) -> str:
        return f" queue max-size-time=3000000000 ! interpipesink name=video_{self.data.uid} async=true sync=true "

    def get_audio_end(self):
        return f" queue max-size-time=3000000000 ! interpipesink name=audio_{self.data.uid} async=true sync=true "


    def add_mixer_pad(self, audio_or_video):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)

        sink_pad_template = mixer.get_pad_template("sink_%u")
        sink_pad = mixer.request_pad(sink_pad_template, None, None)
        if audio_or_video == "video":
            sink_pad.set_property('width', self.data.width)
            sink_pad.set_property('height', self.data.height)
            sink_pad.set_property('operator', "add")
            sink_pad.set_property('alpha', 0)
        sink_pad.set_active(True)

        inputDTO = mixerInputDTO(sink=sink_pad.get_name(), name=sink_pad.get_name())
        self.data.addInput(inputDTO)

        self.update_pad_from_sources(audio_or_video, sink_pad.get_name())

        logger.log(f"Create sink pad {sink_pad.get_name()} in Mixer {self.data.uid}", level='DEBUG')
        return mixerInputDTO(sink=sink_pad.get_name())

    def link_pad(self, audio_or_video, sink_name):
        pipeline = self.get_pipeline()
        sink_pad = self.get_pad(audio_or_video, sink_name)
        if sink_pad.is_linked():
            mixerInputDTO = self.data.getMixerInputDTO(sink_name)
            if self.get_current_input_source(audio_or_video, sink_name) == mixerInputDTO.src:
                return
            else:
                self.unlink_pad(audio_or_video, sink_name)

        src = self.create_source_element(audio_or_video, sink_name)
        self.set_pad_source(audio_or_video, sink_name)
        src.sync_state_with_parent()
        src_pad = src.get_static_pad("src")
        logger.log(f"Linkin sink pad {sink_name} in Mixer {self.data.uid}", level='DEBUG')
        src_pad.link(sink_pad)

    def unlink_pad(self, audio_or_video, sink_name):
        pipeline = self.get_pipeline()

        sink_pad = self.get_pad(audio_or_video, sink_name)
        src = self.get_mixer_source_bin(audio_or_video, sink_name)
        if src:
            src_pad = src.get_static_pad("src")

            sink_pad.send_event(Gst.Event.new_flush_start())
            sink_pad.send_event(Gst.Event.new_flush_stop(True))
            src_pad.unlink(sink_pad)
            src.set_state(Gst.State.NULL)
            pipeline.remove(src)

    def update_pad_from_sources(self, audio_or_video, sink):
            pad = self.get_pad(audio_or_video, sink)
            source = vars(self.data.getMixerInputDTO(sink))
            if audio_or_video == "video":
                properties = ['alpha', 'xpos', 'ypos', 'width', 'height', 'zorder']
            if audio_or_video == "audio":
                properties = ['volume', 'mute']
            source = vars(self.data.getMixerInputDTO(sink))
            for prop in properties:
                if source[prop] is not None:
                    pad.set_property(prop, source[prop])
                else:
                    source[prop] = pad.get_property(prop)
            return pad

    def create_source_element(self, audio_or_video, sink_name):
        src_name = f"{audio_or_video}_{self.data.uid}_{sink_name}_bin"
        pipeline = self.get_pipeline()
        src = pipeline.get_by_name(src_name)
        mixerInputDTO = self.data.getMixerInputDTO(sink_name)
        source = f"{audio_or_video}_{mixerInputDTO.src}"
        if src is None:
            if audio_or_video == "video":
                convert_str = f"   videoconvert ! videoscale !  videorate  "
            elif audio_or_video == "audio":
                convert_str = f" audioresample ! audioconvert !  audiorate "

            src = Gst.parse_bin_from_description(f"interpipesrc name={audio_or_video}_{self.data.uid}_{sink_name}"
            f" max-time=3000000000 handle-segment-change=true format=time allow-renegotiation=true  is-live=true stream-sync=restart-ts do-timestamp=true listen_to={source} !  queue ! "
            f"  {convert_str} ! capsfilter name={audio_or_video}_capsfilter  ! queue  max-size-time=3000000000 ", True) #max-size-time=1000000000
            src.set_name(src_name)
            pipeline.add(src)
            src.sync_state_with_parent()
            self.set_capsfilter(audio_or_video, sink_name)
            logger.log(f"Create source bin {src_name} in Mixer {self.data.uid}", level='DEBUG')
        return src

    def add_source(self, input):
        mixerInputDTO = self.data.getMixerInputDTO(input.sink)
        self.data.update_mixer_input(input.sink, src=input.src)
        for audio_or_video in ["audio", "video"]:
            self.link_pad(audio_or_video, input.sink)
            self.set_pad_source(audio_or_video, input.sink)
            self.update_pad_from_sources(audio_or_video, input.sink)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))

    def getMixer(self, audio_or_video):
        mixerpipe = self.get_pipeline()
        mixer = mixerpipe.get_by_name(f"{audio_or_video}mixer_{ self.data.uid}")
        return mixer

    def add_pads(self, mixerSource: mixerInputDTO = None):
        self.add_mixer_pad("audio")
        dto = self.add_mixer_pad("video")
        # TODO update for api handling
        if mixerSource is not None:
            self.data.update_mixer_input(dto.sink, mixerSource)
        self.data.update_sources_with_defaults()
        asyncio.create_task(manager.broadcast("UPDATE", self.data))
        return dto

    def get_mixer_pad(self, audio_or_video, sink_name):
        mixer = self.getMixer(audio_or_video)
        return mixer.get_static_pad(sink_name)

    def set_pad_source(self, audio_or_video, sink_name):
        src = self.get_mixer_source(audio_or_video, sink_name)
        mixerInputDTO = self.data.getMixerInputDTO(sink_name)
        pad = self.get_pad(audio_or_video, sink_name)
        bin = self.get_mixer_source_bin(audio_or_video, sink_name)

        if audio_or_video == "video":
            pad.set_property("sizing-policy", "keep-aspect-ratio")
        src.set_property("listen-to", f"{audio_or_video}_{mixerInputDTO.src}")
        self.set_capsfilter(audio_or_video, sink_name)

    def get_pad(self, audio_or_video, sink):
        mixer = self.getMixer(audio_or_video)
        return mixer.get_static_pad(sink)

    def get_mixer_source_bin(self, audio_or_video, sink_name):
        pipe = self.get_pipeline()
        bin = pipe.get_by_name(f"{audio_or_video}_{self.data.uid}_{sink_name}_bin")
        return bin

    def get_mixer_source(self, audio_or_video, sink_name):
        bin = self.get_mixer_source_bin(audio_or_video, sink_name)
        src = bin.get_by_name(f"{audio_or_video}_{self.data.uid}_{sink_name}")
        return src

    def get_current_input_source(self, audio_or_video, sink_name):
        src = self.get_mixer_source(audio_or_video, sink_name)
        uid = src.get_property("listen-to")
        try:
            if uid is not None and uid != "None":
                return UUID(uid)
        except ValueError:
            return None

    def set_capsfilter(self, audio_or_video, sink_name):
        mixer = self.getMixer(audio_or_video)
        mixer_src_pad = mixer.get_static_pad("src")
        mixer_caps = mixer_src_pad.get_current_caps()
        if mixer_caps:
            bin = self.get_mixer_source_bin(audio_or_video, sink_name)
            capsfilter = bin.get_by_name(f"{audio_or_video}_capsfilter")
            capsfilter.set_property("caps", mixer_caps)
            logger.log(f"Set pad caps to {mixer_caps.to_string()} for  {sink_name}", level='DEBUG')