
import requests
import sys
import asyncio
import threading
import os
import time
from api.inputs_dtos import PlaylistInputDTO, PlaylistItemDTO
from pipelines.inputs.input import Input
from gi.repository import Gst, GLib

class PlaylistInput(Input):
    data: PlaylistInputDTO


    def build(self):
        pipeline = Gst.Pipeline.new("pipeline")
        uridecodebin = Gst.ElementFactory.make("uridecodebin3", "uridecodebin")
        self.data.index = -1
        uri = self.next_uri()
        uridecodebin.set_property('uri', self.data.playlist[0].uri)
        uridecodebin.set_property('buffer-duration', 6 *Gst.SECOND)
        uridecodebin.set_property('download', True)
        uridecodebin.set_property('use-buffering', True)
        uridecodebin.set_property('async-handling', True)
        uridecodebin.connect("pad-added", self.on_pad_added)
        pipeline.add(uridecodebin)

        videobin = Gst.parse_bin_from_description(f"videoconvert  ! video/x-raw,format=BGRA ! queue ! {self.get_video_end()}", True)
        videobin.set_name("videobin")
        pipeline.add(videobin)
        videobin.sync_state_with_parent()

        audiobin = Gst.parse_bin_from_description(f"audiotestsrc wave=4 ! audioconvert ! audiorate ! audioresample ! audiomixer name=audiomixer  ! audioresample !  {self.get_audio_end()}", True)
        audiobin.set_name("audiobin")
        pipeline.add(audiobin)
        audiobin.sync_state_with_parent()
        self.add_pipeline(pipeline)
        print(pipeline)
                


    def on_pad_added(self, src, pad):
        pad_type = pad.query_caps(None).to_string()
        if "audio" in pad_type:
            if not pad.is_linked():                
                audiobin = self.get_pipeline().get_by_name("audiobin")
                audiomixer = audiobin.get_by_name("audiomixer")
                self.get_mixer_pad(audiomixer)
                audiomixer_sink_pad_template = audiomixer.get_pad_template("sink_%u")
                audiomixer_sink_pad = audiomixer.request_pad(audiomixer_sink_pad_template, None, None)
                
                bin = Gst.parse_bin_from_description(f"queue ! audioconvert ! audiorate ! audioresample  ! queue  ", True)
                bin.set_name("audiopad_bin")
                self.get_pipeline().add(bin)
                bin.sync_state_with_parent()
                audio_sink_pad = bin.get_static_pad("sink")
                audio_src_pad = bin.get_static_pad("src")
                pad.link(audio_sink_pad)
                
                ghost_pad = Gst.GhostPad.new(audiomixer_sink_pad.get_name(), audiomixer_sink_pad)
                ghost_pad.set_active(True)
                audiobin.add_pad(ghost_pad)
                audio_src_pad.link(ghost_pad)

                bin.set_state(Gst.State.PLAYING)


        elif "video" in pad_type and not pad.is_linked():
            videobin = self.get_pipeline().get_by_name("videobin")
            video_queue_sink_pad = videobin.get_static_pad("sink")
            pad.link(video_queue_sink_pad)
            pad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, self.on_event)
      

    async def html_stop_task(self, duration):
        eos_event = Gst.Event.new_eos()
        await asyncio.sleep(duration)
        uridecodebin = self.get_pipeline().get_by_name("uridecodebin")
        uridecodebin.send_event(eos_event)

    async def _jumpToNextPlaylist(self):
        data = self._load_playlist(self.data.next)
        if data is not None:
            next_playlist = [PlaylistItemDTO(**item) for item in data["playlist"]]
            self.data.playlist = next_playlist
            self.data.next = data.get("next")
            self.data.looping = data.get("looping", False)
        self.data.index = 0

    def next_uri(self):
        self.data.index += 1
        if self.data.index >= len(self.data.playlist):
            if self.data.next is not None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._jumpToNextPlaylist())
                self.data.index = 0
            elif self.data.looping:
                self.data.index = 0
        uri = self.data.playlist[self.data.index].uri
        self.data.current_clip = uri
        if self.data.playlist[self.data.index].type == "video":
            if uri.startswith("http"):
                response = requests.head(uri)                
                if response.status_code == 200:
                    return uri
                else:
                    self.next_uri()
            elif uri.startswith("file://"):
                if os.path.isfile(uri.replace("file://", "")):
                    return uri
                else:
                    self.next_uri()
        elif self.data.playlist[self.data.index].type == "html":
             return uri
        else:
            self.next_uri()
    

    def change_uri(self):
        uri = self.next_uri()
        uridecodebin = self.get_pipeline().get_by_name("uridecodebin")
        self.get_pipeline().set_state(Gst.State.READY)
        self.remove_bin()
        if self.data.playlist[self.data.index].type == "html":
            uri = "web+" + uri
        uridecodebin.set_property("uri", uri)
        self.get_pipeline().set_state(Gst.State.PLAYING)
        if self.data.playlist[self.data.index].type == "html":
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)            
            loop.run_until_complete(self.html_stop_task(10))

        return False 

    def on_event(self, pad, info):
        event = info.get_event()
        if event.type == Gst.EventType.EOS:
            eos_event = Gst.Event.new_eos()
            self.wait_until_buffer_empty(self.get_pipeline())
            GLib.idle_add(self.change_uri)
        return Gst.PadProbeReturn.OK

    def _load_playlist(self, uri):
        try:
            r = requests.get(uri)
            if r.status_code == 200:
                return r.json()
            else:
                self.logger.error("Error loading playlist from http server!")
                return None
        except Exception:
            self.logger.error("Error loading playlist from http server!")
            return None

    def remove_bin(self):
        bin = self.get_pipeline().get_by_name("audiopad_bin")
        audiobin = self.get_pipeline().get_by_name("audiobin")
        audiomixer = audiobin.get_by_name("audiomixer")
        mixer_pad = self.get_mixer_pad(audiomixer)        
        if mixer_pad:
            audiomixer_pad = audiomixer.get_static_pad(mixer_pad)
            audiomixer.release_request_pad(audiomixer_pad)
            bin.set_state(Gst.State.NULL)
            self.get_pipeline().remove(bin)
            bin.set_state(Gst.State.NULL)

    def wait_until_buffer_empty(self,pipeline):
        while True:
            uridecodebin = pipeline.get_by_name("uridecodebin")
            success, position = pipeline.query_position(Gst.Format.TIME)
            success, duration = uridecodebin.query_duration(Gst.Format.TIME)
            duration = duration            
            if success and position >= duration:
                break
            time.sleep(0.01)

    def get_mixer_pad(self, element):
        pads = []
        if element is None:
            return []
        iterator = element.iterate_pads()
        while True:
            result, pad = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            if pad.get_name() != "src" and pad.get_name() != "sink_0":
                return pad.get_name()

    def describe(self):

        return self.data
