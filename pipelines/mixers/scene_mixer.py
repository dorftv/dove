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
            f" compositor zero-size-is-unscaled=false background=black force-live=true ignore-inactive-pads=true name=videomixer_{self.data.uid} sink_0::alpha=1 ! videoconvert ! videoscale ! videorate ! { caps }  ! queue !  "
            f" {self.get_video_end()} "
            f" audiotestsrc wave=4 ! { audio_caps } ! audiomixer name=audiomixer_{self.data.uid} !  audioconvert ! audiorate ! audioresample ! { audio_caps } ! queue !  "
            + self.get_audio_end())

        loop = self.data.countMixerInputs()
        if loop is None:
            loop = self.data.n
        for i in range(loop):
            pad = self.add_pads() 

        # TODO update for api creation
        self.data.update_sources_with_defaults()


    def add_source(self, input):
        mixerInputDTO = self.data.getMixerInputDTO(input.sink)
        self.data.update_mixer_input(input.sink, src=input.src)
        for audio_or_video in ["audio", "video"]:
            self.link_pad(audio_or_video, input.sink)
            self.set_pad_source(audio_or_video, input.sink)
            self.update_pad_from_sources(audio_or_video, input.sink)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))
        

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
             

    def remove_mixer_pad(self, audio_or_video, sink_name):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)
        self.unlink_pad(audio_or_video, sink_name)
        sink_pad = self.get_mixer_pad(audio_or_video, sink_name)
        mixer.remove_pad(sink_pad)
        return


    def add_mixer_pad(self, audio_or_video):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)

        sink_pad_template = mixer.get_pad_template("sink_%u")
        sink_pad = mixer.request_pad(sink_pad_template, None, None)
        if audio_or_video == "video":
            sink_pad.set_property('width', self.data.width)
            sink_pad.set_property('height', self.data.height)
            sink_pad.set_property('operator', "add")

        
        inputDTO = mixerInputDTO(sink=sink_pad.get_name(), name=sink_pad.get_name())
        self.data.addInput(inputDTO)
        
        self.update_pad_from_sources(audio_or_video, sink_pad.get_name())        

        logger.log(f"Create sink pad {sink_pad.get_name()} in Mixer {self.data.uid}", level='DEBUG')            
        return mixerInputDTO(sink=sink_pad.get_name())


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
                convert_str = f" audioresample ! audioconvert !  audiorate ! queue max-size-time=300000000"

            src = Gst.parse_bin_from_description(f"interpipesrc name={audio_or_video}_{self.data.uid}_{sink_name}"
            f" max-time=2000000000 format=time allow-renegotiation=true leaky-type=upstream  is-live=true stream-sync=restart-ts do-timestamp=true listen-to={source} !  "
            f"  {convert_str} ! capsfilter name={audio_or_video}_capsfilter ! queue  ", True)
            src.set_name(src_name)
            pipeline.add(src)
            logger.log(f"Create source bin {src_name} in Mixer {self.data.uid}", level='DEBUG')
        return src


    def set_capsfilter(self, audio_or_video, sink_name):
        mixer = self.getMixer(audio_or_video)
        mixer_src_pad = mixer.get_static_pad("src")
        mixer_caps = mixer_src_pad.get_current_caps()
        if mixer_caps:
            bin = self.get_mixer_source_bin(audio_or_video, sink_name)
            capsfilter = bin.get_by_name(f"{audio_or_video}_capsfilter")
            capsfilter.set_property("caps", mixer_caps)
            logger.log(f"Set pad caps to {mixer_caps.to_string()} for  {sink_name}", level='DEBUG')            


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

    def describe(self):
        return self.data
