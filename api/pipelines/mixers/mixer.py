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
        print(f"check: {src}  {uid}")

    async def handle_websocket(self):
        await manager.broadcast("UPDATE", self.data)

        
    def cut(self, input):

        print("----CUT-----")
        try:
            print("CUT VIDEOS")            
            self.cut_interpipe("video", input)

            print("CUT AUDIO")
            self.cut_interpipe("audio", input)

            self.data.cut_source(input.src)
            print(self.data)
            asyncio.create_task(manager.broadcast("UPDATE", self.data))

        except ValueError as e:
            print(e)


    def cut_interpipe(self, audio_or_video, input):
        mixer = self.getMixer(audio_or_video)
        pads =  self.get_pads(mixer)
        for pad in pads:
            print(f"PAD: {pad.get_name()}")

        if len(pads) == 2:
            src = self.createInterpipesrc(audio_or_video, input)
        else:
            src =  self.getInterpipesrc(audio_or_video, input)

        if src:
            self.updateInterpipesrc(audio_or_video, input)

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

    def updateInterpipesrc(self, audio_or_video, input):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)
        mixer_src_pad = mixer.get_static_pad("src")
        src = mixerpipe.get_by_name(f"{audio_or_video}_{input.target}_bin")
        capsfilter = src.get_by_name(f"{audio_or_video}_capsfilter")
        
        mixer_src_pad = mixer.get_static_pad("src")
        mixer_caps = mixer_src_pad.get_current_caps()
        print("UPDATE")
        print(mixer_caps.to_string)
        capsfilter.set_property("caps", mixer_caps)
        element = self.getInterpipesrc(audio_or_video, input)
        element.set_property("listen-to", f"{audio_or_video}_{input.src}" )


    def getInterpipesrc(self, audio_or_video, input):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)
        pads = self.get_pads(mixer)
        print(pads)
        sink1_pad = mixer.get_static_pad("sink_1")
        bin = sink1_pad.get_peer().get_parent()
        element = bin.get_by_name(f"{audio_or_video}_{input.target}_src") 
        return element

    def deleteInterpipesrcs(self, audio_or_video, input):
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)        
        pads = self.get_pads(mixer)
        exclude = ["src", "sink_0", "sink_1"]
        for pad in pads:
            if pad.get_name() in exclude:
                continue
        src_pad = pad.get_peer()
        if src_pad:
            element_remove = src_pad.get_peer().get_parent()
            if element_remove:
                mixer.release_request_pad(src_pad)
                element_remove.set_state(Gst.State.NULL)
                mixerpipe.remove(element_remove)              

   
    def getMixer(self, audio_or_video):
        mixerpipe = self.get_pipeline()
        mixer = mixerpipe.get_by_name(f"{audio_or_video}mixer_{ self.uid}")
        return mixer


    def createInterpipesrc(self, audio_or_video, input):
        #caps = "video/x-raw,width=1280,height=720,framerate=25/1"
        audio_caps = "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2"
        mixerpipe = self.get_pipeline()
        mixer = self.getMixer(audio_or_video)
     
        # Get the current caps of the compositor's sink pad
        sink_pad_template = mixer.get_pad_template("sink_%u")
        sink_pad = mixer.request_pad(sink_pad_template, None, None)
        self.data.update_mixer_input(input.src, sink=sink_pad.get_name())
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
            
            mixerpipe = self.inner_pipelines[0]
            print(mixerpipe)
            mixer = self.getMixer("video")
            self.deleteInterpipesrcs("video", input, mixer, mixerpipe);

            

        except ValueError as e:
            print(e)
        asyncio.create_task(manager.broadcast("UPDATE", self.data))
        

    def describe(self):

        return self.data        