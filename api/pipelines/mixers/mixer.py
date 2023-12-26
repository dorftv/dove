from api.mixers_dtos import mixerCutDTO, mixerInputsDTO, mixerInputDTO, mixerDTO
from pipelines.base import GSTBase
from abc import ABC
from gi.repository import Gst, GLib
from api.websockets import manager
import asyncio
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator, validator


class Mixer(GSTBase, ABC):
    uid: UUID
    #data: mixerDTO
    


    def get_video_end(self) -> str:
        return f" queue ! interpipesink name=video_{self.data.uid} async=false sync=true"

    def get_audio_end(self):
        return f" queue ! interpipesink name=audio_{self.data.uid} async=false sync=true"
    def describe(self):
        return self
    def test(self, handler, uid, src):
        print(f"check: {src}  {uid}")

    async def handle_websocket(self):
        await manager.broadcast("UPDATE", self.data)


        
    def cut(self, input):

        print("----CUT-----")
        try:
            self.data.cut_source(input.src)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))
            mixerpipe = self.inner_pipelines[0]
            print("CUT VIDEOS")
            
            self.cut_interpipe("video", input, mixerpipe)
            #audiomixer = self.getMixer("audio", mixerpipe)            
            print("CUT AUDIO")
            self.cut_interpipe("audio", input, mixerpipe)

             
 #               src.set_property("listen-to", input.src)

        except ValueError as e:
            print(e)
    def cut_interpipe(self, audio_or_video, input, mixerpipe):
        mixer = self.getMixer(audio_or_video, mixerpipe)
        pads =  self.get_pads(mixer)
        for pad in pads:
            print(f"PAD: {pad.get_name()}")

        #print(pads)
        if len(pads) == 2:
            src = self.createInterpipesrc(audio_or_video, input, mixerpipe)
        else:
            src =  self.getInterpipesrc(audio_or_video, input, mixer, mixerpipe)

        if src:
            self.updateInterpipesrc(audio_or_video, input, mixer, mixerpipe)

        pads =  self.get_pads(mixer)
        for pad in pads:
            print(f"PAD: {pad.get_name()}")


    def get_pads(self, element):
        pads = []
        iterator = element.iterate_pads()
        while True:
            result, pad = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            print(pad.get_name())
            pads.append(pad)
        return pads

    def updateInterpipesrc(self, audio_or_video, input, mixer, mixerpipe):
        mixer_src_pad = mixer.get_static_pad("src")

        src = mixerpipe.get_by_name(f"{audio_or_video}_{input.target}_bin")

        capsfilter = src.get_by_name(f"{audio_or_video}_capsfilter")
        mixer_src_pad = mixer.get_static_pad("src")
        mixer_caps = mixer_src_pad.get_current_caps()
        capsfilter.set_property("caps", mixer_caps)

        element = self.getInterpipesrc(audio_or_video, input, mixer, mixerpipe)
        element.set_property("listen-to", f"{audio_or_video}_{input.src}" )


    def getInterpipesrc(self, audio_or_video, input, mixer, mixerpipe):
        pads = self.get_pads(mixer)
        print(pads)
        if audio_or_video == "video":
            sink1_pad = mixer.get_static_pad("sink_1")
            bin = sink1_pad.get_peer().get_parent()
        elif audio_or_video == "audio":
            sink1_pad = mixer.get_static_pad("sink_0") 
            bin = sink1_pad.get_peer().get_parent().get_parent()
            print(bin)
            
        if sink1_pad:      
            
            print(bin)
            element = bin.get_by_name(f"{audio_or_video}_{input.target}_src")
            print(element)


        element = bin.get_by_name(f"{audio_or_video}_{input.target}_src") 
        return element


   
    def getMixer(self, audio_or_video, mixerpipe):
        mixer = mixerpipe.get_by_name(f"{audio_or_video}mixer_{ self.uid}")
        return mixer


    def createInterpipesrc(self, audio_or_video, input, mixerpipe):
        #caps = "video/x-raw,width=1280,height=720,framerate=25/1"
        audio_caps = "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2"
        
        # Create Elements
        #VIDEO same as Video but videosrc && videomixer variable
        #videomixer_pad = videomixer.get_static_pad("sink_0")
        #videomixer_caps = videomixer_pad.get_current_caps()
        mixer = self.getMixer(audio_or_video, mixerpipe)
     
        # Get the current caps of the compositor's sink pad
        sink_pad_template = mixer.get_pad_template("sink_%u")
        sink_pad = mixer.request_pad(sink_pad_template, None, None)    
        mixer_src_pad = mixer.get_static_pad("src")
        mixer_caps = mixer_src_pad.get_current_caps()
        if mixer_caps is not None:
            print("Current Caps: ", mixer_caps.to_string())
        else:
            print("No caps available on the compositor sink pad.")
        if audio_or_video == "video":
            convert_str = "videoconvert !  videoscale ! videorate"
        elif audio_or_video == "audio":
            convert_str = "audioconvert !  audioresample "

        src = Gst.parse_bin_from_description(f"interpipesrc name={audio_or_video}_{input.target}_src"
        f" format=time allow-renegotiation=true is-live=true stream-sync=restart-ts ! "
        f"  {convert_str} ! capsfilter name={audio_or_video}_capsfilter ! queue  ", True)
        src.set_name(f"{audio_or_video}_{input.target}_bin")
        interpipesrc = src.get_by_name(f"{audio_or_video}_{input.target}_src")
        capsfilter = src.get_by_name(f"{audio_or_video}_capsfilter")
        capsfilter.set_property("caps", mixer_caps)

        mixerpipe.add(src)
        src_pad =src.get_static_pad("src")
        src_pad.link(sink_pad)
        src.sync_state_with_parent()   
        return interpipesrc

    def overlay(self, input):
        print("-----")
        try:
            self.data.overlay_source(input.src)
            print(self.data.sources)
        except ValueError as e:
            print(e)
        asyncio.create_task(manager.broadcast("UPDATE", self.data))
        
    def remove(self, input):
        print("-----")
        try:
            self.data.remove_source(input.src)
            print(self.data.sources)
        except ValueError as e:
            print(e)
        asyncio.create_task(manager.broadcast("UPDATE", self.data))
        
    #prepares the interpipesrc and interpipesink connection
    # TODO Refactor this is mostly duplicate!!! use audio_or_video like Brave
    def addInputToMix(self, mixerpipe, videomixer, srcUid):
        # @TODO improve caps handling
        caps = "video/x-raw,width=1280,height=720,framerate=25/1"
        audio_caps = "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2"
        
        # Create Elements
        #VIDEO same as Video but videosrc && videomixer variable
        #videomixer_pad = videomixer.get_static_pad("sink_0")
        #videomixer_caps = videomixer_pad.get_current_caps()
        videosrc = Gst.parse_bin_from_description(f"interpipesrc name=video_{srcUid}_src listen-to=video_{srcUid}  "
        f" format=time allow-renegotiation=false do-timestamp=true is-live=true "
        f" ! videoconvert !  videoscale ! videorate !  { caps } ! queue   ", True)
        videosrc.set_name(f"video_{srcUid}_bin")
        mixerpipe.add(videosrc)
        pads =  get_pads(mixerpipe)
        print(pads)
        sink_pad_template = videomixer.get_pad_template("sink_%u")
        sink_pad = videomixer.request_pad(sink_pad_template, None, None)    
        src_pad = videosrc.get_static_pad("src")
    
 #       #audiomixer_pad = audiomixer.get_static_pad("sink_0")
 #       #audiomixer_caps = audiomixer_pad.get_current_caps()
 #       audiosrc = Gst.parse_bin_from_description(f"interpipesrc name=audio_{uid}_src listen-to=audio_{uid}  "
 #       f" format=time allow-renegotiation=false do-timestamp=true is-live=true "
 #       f" ! audioconvert ! audiorate ! queue ", True)
 #       audiosrc.set_name(f"audio_{uid}_bin")
 #       mixerpipe.add(audiosrc)
 #       audio_sink_pad_template = audiomixer.get_pad_template("sink_%u")
 #       audio_sink_pad = audiomixer.request_pad(audio_sink_pad_template, None, None)
 #       audio_src_pad = audiosrc.get_static_pad("src")
 #        
 #       # link audio and video
        src_pad.link(sink_pad)
        videosrc.sync_state_with_parent()     
 #       audio_src_pad.link(audio_sink_pad)
 #       audiosrc.sync_state_with_parent() 
 #       # used by cut



    def describe(self):

        return self.data        