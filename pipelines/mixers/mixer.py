from logger import logger
from api.mixers_dtos import mixerCutDTO, mixerSlotDTO, mixerInputsDTO, mixerInputDTO, mixerDTO
from pipelines.base import GSTBase
from abc import ABC
from gi.repository import Gst, GLib
from api.websockets import manager
import asyncio
from uuid import UUID, uuid4



class Mixer(GSTBase, ABC):
    data: mixerDTO


    def get_video_end(self) -> str:
        return f" queue max-size-time=300000000 ! interpipesink name=video_{self.data.uid} async=true sync=true  max-buffers=10 drop=true"

    def get_audio_end(self):
        return f" queue max-size-time=300000000 ! interpipesink name=audio_{self.data.uid} async=true sync=true  max-buffers=10 drop=true "


    def add_slot(self, mixerSource: mixerInputDTO = None):
        self.data.add_slot(mixerSource)
        asyncio.create_task(manager.broadcast("UPDATE", self.data))

    def remove_slot(self, mixerSource: mixerInputDTO = None):
        #source = self.data.getMixerInputDTO(mixerSlot.index)
        self.data.remove_slot(mixerSource)
        asyncio.create_task(manager.broadcast("UPDATE", self.data))

    def add_source(self, input: mixerCutDTO):
        mixerInputDTO = self.data.getMixerInputDTO(input.index)
        self.data.update_mixer_input(input.index, src=input.src)
        for audio_or_video in ["audio", "video"]:
            sink = self.add_mixer_pad(audio_or_video, input.index)
            self.link_pad(audio_or_video, input.index)
            self.update_pad_from_sources(audio_or_video, input.index)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))

    def remove_source(self, input):
        if input.index is not None:
            mixerInputDTO = self.data.getMixerInputDTO(input.index)
        if mixerInputDTO is not None:
            for audio_or_video in ["audio", "video"]:
                self.data.update_mixer_input(input.index, src="None")
                self.update_pad_from_sources(audio_or_video, input.index)
                self.unlink_pad(audio_or_video, mixerInputDTO.sink)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))

    def add_mixer_pad(self, audio_or_video, index):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)

        sink_pad_template = mixer.get_pad_template("sink_%u")
        sink_pad = mixer.request_pad(sink_pad_template, None, None)
        if audio_or_video == "video":
            sink_pad.set_property('operator', "add")
            sink_pad.set_property("sizing-policy", "keep-aspect-ratio")

        sink_pad.set_active(False)
        self.data.update_mixer_input(index, sink=sink_pad.get_name())
        self.update_pad_from_sources(audio_or_video, index)
        logger.log(f"Create sink pad {sink_pad.get_name()} in Mixer {self.data.uid}", level='DEBUG')
        return sink_pad.get_name()

    def link_pad(self, audio_or_video, index):
        pipeline = self.get_pipeline()
        mixerInputDTO = self.data.getMixerInputDTO(index)
        sink = mixerInputDTO.sink
        sink_pad = self.get_pad(audio_or_video, sink)
        src = self.create_source_element(audio_or_video, index)
        self.set_pad_source(audio_or_video, index)
        #src.set_state(Gst.State.PLAYING)
        src.sync_state_with_parent()
        src_pad = src.get_static_pad("src")
        sink_pad.set_active(True)
        logger.log(f"Linkin sink pad {sink_pad.get_name()} in Mixer {self.data.uid}", level='DEBUG')
        src_pad.link(sink_pad)

    def unlink_pad(self, audio_or_video, sink):
        pipeline = self.get_pipeline()
        sink_pad = self.get_pad(audio_or_video, sink)
        src = self.get_mixer_source_bin(audio_or_video, sink)
        if src:

            src_pad = src.get_static_pad("src")
            eos_event = Gst.Event.new_eos()
            sink_pad.send_event(eos_event)
            sink_pad.set_active(False)
            sink_pad.send_event(Gst.Event.new_flush_start())
            sink_pad.send_event(Gst.Event.new_flush_stop(True))
            src_pad.unlink(sink_pad)
            src.set_state(Gst.State.NULL)
            src.send_event(Gst.Event.new_flush_start())
            src.send_event(Gst.Event.new_flush_stop(True))
            src.get_state(timeout=Gst.CLOCK_TIME_NONE)



        # Remove all elements from the bin (src)
            iterator = src.iterate_recurse()
            while True:
                try:
                    result = iterator.next()
                    if result == Gst.IteratorResult.OK:
                        elem, _ = iterator.get_current()
                        if elem != src:
                            peer = elem.get_peer()
                            if peer:
                                elem.unlink(peer)
                            src.remove(elem)
                    else:
                        break
                except StopIteration:
                    break
            pipeline.remove(src)
        if sink_pad:
            mixer = self.getMixer(audio_or_video)
            mixer.release_request_pad(sink_pad)
        sink_pad = None
        src_pad = None
        src = None


        import gc
        gc.collect()


    def update_pad_from_sources(self, audio_or_video, index):
            mixerInputDTO = self.data.getMixerInputDTO(index)
            sink = mixerInputDTO.sink
            pad = self.get_pad(audio_or_video, sink)
            if pad:
                source = vars(self.data.getMixerInputDTO(index))
                if audio_or_video == "video":
                    properties = ['alpha', 'xpos', 'ypos', 'width', 'height', 'zorder']
                if audio_or_video == "audio":
                    properties = ['volume', 'mute']
                source = vars(self.data.getMixerInputDTO(index))
                for prop in properties:
                    if source[prop] is not None:
                        pad.set_property(prop, source[prop])
                    else:
                        source[prop] = pad.get_property(prop)
                return pad

    def create_source_element(self, audio_or_video, index):
        pipeline = self.get_pipeline()
        mixerInputDTO = self.data.getMixerInputDTO(index)
        sink_name = mixerInputDTO.sink
        src_name = f"{audio_or_video}_{self.data.uid}_{sink_name}_bin"
        src = pipeline.get_by_name(src_name)
        source = f"{audio_or_video}_{mixerInputDTO.src}"
        if src is None:
            if audio_or_video == "video":
                convert_str = f"   videoconvert ! videoscale !  videorate  "
            elif audio_or_video == "audio":
                convert_str = f" audioresample ! audioconvert !  audiorate "

            src = Gst.parse_bin_from_description(f"interpipesrc name={audio_or_video}_{self.data.uid}_{sink_name}"
            f" leaky-type=downstream max-buffers=0 max-bytes=0 max-time=500000000  format=time stream-sync=restart-ts listen_to={source} ! "
            f"  {convert_str} ! capsfilter name={audio_or_video}_capsfilter  ! queue max-size-buffers=0 max-size-bytes=0 max-size-time=500000000 leaky=upstream ", True)
            src.set_name(src_name)
            src.set_clock(self.get_clock())
            pipeline.add(src)
            self.set_capsfilter(audio_or_video, sink_name)
            logger.log(f"Create source bin {src_name} in Mixer {self.data.uid}", level='DEBUG')
        return src

    def getMixer(self, audio_or_video):
        mixerpipe = self.get_pipeline()
        mixer = mixerpipe.get_by_name(f"{audio_or_video}mixer_{ self.data.uid}")
        return mixer

    def set_pad_source(self, audio_or_video, index):
        src = self.get_mixer_source(audio_or_video, index)
        mixerInputDTO = self.data.getMixerInputDTO(index)
        src.set_property("listen-to", f"{audio_or_video}_{mixerInputDTO.src}")
        self.set_capsfilter(audio_or_video, mixerInputDTO.sink)

    def get_pad(self, audio_or_video, sink):
        mixer = self.getMixer(audio_or_video)
        return mixer.get_static_pad(sink)

    def get_mixer_source_bin(self, audio_or_video, sink):
        pipe = self.get_pipeline()
        bin = pipe.get_by_name(f"{audio_or_video}_{self.data.uid}_{sink}_bin")
        return bin

    def get_mixer_source(self, audio_or_video, index):
        mixerInputDTO = self.data.getMixerInputDTO(index)
        sink = mixerInputDTO.sink
        bin = self.get_mixer_source_bin(audio_or_video, sink)
        src = bin.get_by_name(f"{audio_or_video}_{self.data.uid}_{sink}")
        return src

    def get_current_input_source(self, audio_or_video, index):
        src = self.get_mixer_source(audio_or_video, index)
        uid = src.get_property("listen-to")
        try:
            if uid is not None and uid != "None":
                return UUID(uid)
        except ValueError:
            return None

    def set_capsfilter(self, audio_or_video, sink):
        mixer = self.getMixer(audio_or_video)
        mixer_src_pad = mixer.get_static_pad("src")
        bin = self.get_mixer_source_bin(audio_or_video, sink)
        capsfilter = bin.get_by_name(f"{audio_or_video}_capsfilter")
        capsfilter_sink_pad = capsfilter.get_static_pad("sink")

        # Get the peer pad of the capsfilter sink pad
        peer_pad = capsfilter_sink_pad.get_peer()

        # Get the current caps of the peer pad
        negotiated_caps = peer_pad.get_current_caps()

        if negotiated_caps:
            capsfilter.set_property("caps", negotiated_caps)
            logger.log(f"Set pad caps to {negotiated_caps.to_string()} for {sink}", level='DEBUG')
