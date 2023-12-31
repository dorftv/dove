from logger import logger
from api.mixers_dtos import mixerCutDTO, mixerInputsDTO, mixerInputDTO, mixerDTO
from pipelines.base import GSTBase
from abc import ABC
from gi.repository import Gst, GLib
from api.websockets import manager
import asyncio
from uuid import UUID, uuid4
from pipeline_main import get_pipeline_handler





class Mixer(GSTBase, ABC):

    data: mixerDTO
    
    def get_video_end(self) -> str:
        return f" queue ! interpipesink name=video_{self.data.uid} async=false sync=true"

    def get_audio_end(self):
        return f" queue ! interpipesink name=audio_{self.data.uid} async=false sync=true"
    def describe(self):
        return self

    def test(self, handler, uid, src):
        print(f"check: {src}  {data.uid}")

    async def handle_websocket(self):
        await manager.broadcast("UPDATE", self.data)

    def cut(self, input):
        logger.log(f"CUT: add {input.src} to {self.data.uid}" )

        try:
            if self.data.cut_source(input.src):
                self.createInterpipesrc("video", input.src)
            self.sync_pads("video")
            asyncio.create_task(manager.broadcast("UPDATE", self.data))
        except ValueError as e:
            print(e)

    def overlay(self, input):
        logger.log(f"OVERLAY: add {input.src} to {self.data.uid}" )
        try:
            self.data.overlay_source(input.src)
            self.sync_pads("video")
            asyncio.create_task(manager.broadcast("UPDATE", self.data))
        except ValueError as e:
            print(e)


    def remove(self, input):
        logger.log(f"REMOVE: remove {input.src} from {self.data.uid}" )
        try:
            self.data.remove_source(input.src)
            self.sync_pads("video")
            asyncio.create_task(manager.broadcast("UPDATE", self.data))
        except ValueError as e:
            print(e)

    # Sync Pads with the content of mixer.sources
    def sync_pads(self, audio_or_video):
            current_pads = self.get_current_pads(self.getMixer(audio_or_video))
            current_sources = {self.get_src_from_pad(pad): pad for pad in current_pads}
            desired_sources = {str(src.src): src for src in self.data.sources}
    
            # Create pads that should be there but aren't
            for src_name in set(desired_sources.keys()) - set(current_sources.keys()):
                self.createInterpipesrc(audio_or_video, src_name)
        
            # Update pads that are already there and should be there
            for src_name in set(desired_sources.keys()) & set(current_sources.keys()):
                logger.log(f"Update {src_name} already in mix {self.data.uid}" )
                self.updateInterpipesrc(audio_or_video, src_name)
                #self.updatePad(audio_or_video, current_sources[src_name], src_name)
        
            # Delete pads that shouldn't be there
            for src_name in set(current_sources.keys()) - set(desired_sources.keys()):
                if src_name:
                    pad = current_sources[src_name]
                    logger.log(f"remove {self.get_src_from_pad(pad)} from {self.data.uid}" )
                    self.deleteInterpipesrc(audio_or_video, pad)
    
    # get src pipeline name ( uid )
    def get_src_from_pad(self, pad):
        if pad:
            peer = pad.get_peer()
            
            if peer:
                parent = peer.get_parent_element()
                if parent:
                    name = parent.get_name()
                    return self.extract_uuid(name) 

    def extract_uuid(self, s):
        parts = s.split('_')
        return parts[1] if len(parts) > 1 else None

    # gets pads from mixer 
    # exclude src pad and sink_0
    def get_current_pads(self, element):
        pads = []
        if element is None:
            return []
        iterator = element.iterate_pads()
        while True:
            result, pad = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            if pad.get_name() != "src" and pad.get_name() != "sink_0":
                pads.append(pad)
        return pads


    def deleteInterpipesrc(self, audio_or_video, pad):
        src_pad = pad.get_peer()
        
        if src_pad is not None:
            element_remove = src_pad.get_parent_element()
            if element_remove:
                mixer = self.getMixer(audio_or_video)
                mixerpipe = self.get_pipeline()
                mixer.release_request_pad(pad)
                element_remove.set_state(Gst.State.NULL)
                mixerpipe.remove(element_remove)              



    def updateInterpipesrc(self, audio_or_video, inputsrc):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)
        mixer_src_pad = mixer.get_static_pad("src")
        src = mixerpipe.get_by_name(f"{audio_or_video}_{inputsrc}_bin")
        capsfilter = src.get_by_name(f"{audio_or_video}_capsfilter")
        mixer_src_pad = mixer.get_static_pad("src")
        mixer_caps = mixer_src_pad.get_current_caps()
        capsfilter.set_property("caps", mixer_caps)
        element = self.getInterpipesrc(audio_or_video, inputsrc)
        element.set_property("listen-to", f"{audio_or_video}_{inputsrc}" )


    def getInterpipesrc(self, audio_or_video, inputsrc):
        mixerpipe = self.get_pipeline()
        bin = mixerpipe.get_by_name(f"{audio_or_video}_{inputsrc}_bin")
        if bin:
            element = bin.get_by_name(f"{audio_or_video}_{inputsrc}_src") 
            if element: 
                return element
        
    def createInterpipesrc(self, audio_or_video, inputsrc):
        logger.log(f"create input {inputsrc} in {self.data.uid}" )
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)

        # Get the current caps of the compositor's sink pad
        sink_pad_template = mixer.get_pad_template("sink_%u")
        sink_pad = mixer.request_pad(sink_pad_template, None, None)
        mixer_src_pad = mixer.get_static_pad("src")
        mixer_caps = mixer_src_pad.get_current_caps()
        if mixer_caps is not None:
            logger.log(f"Current Caps: {mixer_caps.to_string()}")
        else:
            logger.log(f"Current Caps: Not found")            
        if audio_or_video == "video":
            convert_str = "videoconvert !  videoscale ! videorate"
        elif audio_or_video == "audio":
            convert_str = "audioconvert !  audioresample "

        src = Gst.parse_bin_from_description(f"interpipesrc name={audio_or_video}_{inputsrc}_src"
        f" format=time allow-renegotiation=true is-live=true stream-sync=restart-ts ! "
        f"  {convert_str} ! capsfilter name={audio_or_video}_capsfilter ! queue  ", True)
        src.set_name(f"{audio_or_video}_{inputsrc}_bin")
        interpipesrc = src.get_by_name(f"{audio_or_video}_{inputsrc}_src")
        capsfilter = src.get_by_name(f"{audio_or_video}_capsfilter")
        capsfilter.set_property("caps", mixer_caps)
        interpipesrc.set_property("listen-to", f"{audio_or_video}_{inputsrc}" )
        self.update_sources_from_pad(audio_or_video, inputsrc, sink_pad)
        mixerpipe.add(src)
        src_pad = src.get_static_pad("src")
        src_pad.link(sink_pad)
        src.sync_state_with_parent()
        return interpipesrc

    def getMixer(self, audio_or_video):
        mixerpipe = self.get_pipeline()
        mixer = mixerpipe.get_by_name(f"{audio_or_video}mixer_{ self.data.uid}")
        return mixer


    def update_sources_from_pad(self, audio_or_video, inputsrc, pad):
        if audio_or_video == "video":
            uuid = inputsrc
            self.data.update_mixer_input(uuid, 
                alpha = pad.get_property("alpha"),
                width = pad.get_property("width"),
                height = pad.get_property("height"),
                xpos = pad.get_property("xpos"),
                ypos = pad.get_property("ypos"),
                zorder = pad.get_property("zorder"))


    def describe(self):

        return self.data        