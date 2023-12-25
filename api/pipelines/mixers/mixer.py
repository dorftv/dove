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
        print("-----")
        try:
            self.data.cut_source(input.src)
            print(self.data.sources)
        except ValueError as e:
            print(e)
        asyncio.create_task(manager.broadcast("UPDATE", self.data))
        mixerpipe = self.inner_pipelines[0]

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

    def remove_all_interpipes(self, mixerpipe, mixer):
        # Iterate from start_number to end_number
        for pad in self.get_pads(mixer):
            peer = pad.get_peer()
            if peer:
                src_pad = pad.get_peer()
                element = pad.get_peer().get_parent()
                mixer.release_request_pad(pad)
                if element:
                    element.set_state(Gst.State.NULL)
                    mixerpipe.remove(element)
        #self.mixerpipe.set_state(Gst.State.PLAYING)
        # used by remove(uid)
    def remove_element_from_mixer(mixer, audio_or_video, uid):
        element = mixerpipe.get_by_name(f'{audio_or_video}_{uid}_bin')
        if element:
            src_pad = element.get_static_pad('src').get_peer()
            if src_pad:
                element_remove = src_pad.get_peer().get_parent()
                if element_remove:
                    mixer.release_request_pad(src_pad)
                    element_remove.set_state(Gst.State.NULL)
                    mixerpipe.remove(element_remove)

    def get_pads(self, element):
        pads = []
        iterator = element.iterate_pads()
        while True:
            result, pad = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            if pad.get_name() != "src" and pad.get_name() != "sink_0":
              print(pad.get_name())
              pads.append(pad)
        return pads

    def describe(self):

        return self.data        