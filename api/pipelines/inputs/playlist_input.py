
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
        pipeline = Gst.parse_launch(f"input-selector name=video_selector sync-streams=false cache-buffers=true sync-mode=1 cache-buffers=true ! videoconvert !  queue ! {self.get_video_end()} "
            f" input-selector sync-streams=false cache-buffers=true sync-mode=1  cache-buffers=true name=audio_selector ! audioconvert ! queue ! {self.get_audio_end()} ")

        self.add_pipeline(pipeline)
        self.create_selector_pads("video")
        self.create_selector_pads("audio")
        # @TODO Fix first item is HTML
        if self.data.playlist[0].type == "html":
            self.create_html(self.data.playlist[0].uri, "sink_1")
        self.create_uri(None)
        self.set_playlist_item()

    def pipeline_state(self):
        self.get_pipeline().set_state(Gst.State.PLAYING)
        pass

    def on_pad_added(self, src, pad, sink_pads):
        pad_type = pad.query_caps(None).to_string()
        if "audio" in pad_type:
            if not pad.is_linked():
                pad.link(sink_pads["audio"])
        elif "video" in pad_type and not pad.is_linked():
            pad.link(sink_pads["video"])

    def create_uri(self, uri):
        def link_queue(audio_or_video):
            queue = Gst.ElementFactory.make("queue", f"{audio_or_video}_queue")
            queue_sink_pad = queue.get_static_pad("sink")
            self.get_pipeline().add(queue)
            queue_src_pad = queue.get_static_pad("src")
            queue_src_pad.link(self.get_selector_pad(audio_or_video, "sink_0"))
            return queue_sink_pad

        uridecodebin = Gst.ElementFactory.make("uridecodebin3", "uridecodebin")
        uridecodebin.set_name("uridecodebin")
        uridecodebin.set_property("uri", uri)
        uridecodebin.set_property("download", True)
        uridecodebin.set_property("buffer-duration", 3 * Gst.SECOND)
        uridecodebin.set_property("instant-uri", True)
        uridecodebin.set_property("async-handling", True)
        uridecodebin.connect("about-to-finish", lambda b: self.run_on_master(self._on_about_to_finish, b))
        uridecodebin.connect("pad-added", self.on_pad_added, {"audio": link_queue("audio"), "video": link_queue("video")})
        self.get_pipeline().add(uridecodebin)


    def create_html(self, uri, sink):
        def link_queue(audio_or_video):
            queue = wpesrc.get_by_name(f"html_{audio_or_video}_queue")
            pad = queue.get_static_pad("src")
            src_pad = Gst.GhostPad.new(f"{sink}_{audio_or_video}_src", pad)
            wpesrc.add_pad(src_pad)
            src_pad.link(self.get_selector_pad(audio_or_video, sink))
            pass
        print("Create Html")
        caps_string =  "video/x-raw"
        caps = Gst.caps_from_string(caps_string)
        wpesrc = Gst.parse_bin_from_description(f"wpesrc location={uri}  ! "
        " videoconvert ! videoscale ! videorate ! video/x-raw,width=1280,height=720,framerate=30/1,mode=BGRA ! "
        " videoconvert ! videoscale ! videorate ! capsfilter name=capsfilter  ! queue name=html_video_queue "
        " audiotestsrc samplesperbuffer=441 is-live=true wave=4 ! audioconvert ! queue name=html_audio_queue", False)
        wpesrc.set_property("async-handling", True)
        wpesrc.set_name(f"pad_{sink}")
        capsfilter = wpesrc.get_by_name("capsfilter")
        capsfilter.set_property("caps", caps)
        self.get_pipeline().add(wpesrc)
        link_queue("video")
        link_queue("audio")

        self.get_pipeline().set_state(Gst.State.PLAYING)

    async def html_stop_task(self):
        item = self.data.playlist[self.index]
        await asyncio.sleep(item.get("duration", 5))
        eos_event = Gst.Event.new_eos()
        self.pipeline.send_event(eos_event)

    async def _jumpToNextPlaylist(self):
        data = self._load_playlist(self.data.next)
        if data is not None:
            next_playlist = [PlaylistItemDTO(**item) for item in data["playlist"]]
            self.data.playlist = next_playlist
            self.data.next = data.get("next")
            self.data.looping = data.get("looping", False)
        self.data.index = 0

    def create_selector_pads(self, audio_or_video):
        for i in range(3):
            selector = self.get_pipeline().get_by_name(f"{audio_or_video}_selector")
            template = selector.get_pad_template("sink_%u")
            selector.request_pad(template, None, None)
        pass

    def get_selector_pad(self, audio_or_video, sink):
        selector = self.get_pipeline().get_by_name(f"{audio_or_video}_selector")
        sink = selector.get_static_pad(sink)
        return sink

    def get_active_pad(self):
        video_selector = self.get_pipeline().get_by_name("video_selector")
        active_pad = video_selector.get_property("active-pad")
        return active_pad

    def get_html_sink(self):
        active_pad = self.get_active_pad()
        if active_pad == None:
            return "sink_1"
        active_pad_name = active_pad.get_name()
        if active_pad_name == "sink_0" or active_pad_name == "sink_2":
            sink = "sink_1"
        else:
            sink = "sink_2"
        return sink

    # @TODO prevent constant EOS changes
    def _on_state_change(self, bus, message):
        pass

    def _on_about_to_finish(self, src):
        self.data.index += 1

        if self.data.index >= len(self.data.playlist):
            if self.data.next is not None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._jumpToNextPlaylist())
                self.data.index = 0
            elif self.data.looping:
                self.data.index = 0
        if self.data.playlist[self.data.index].type == "html":
            self.create_html(self.data.playlist[self.data.index].uri, self.get_html_sink())

    def set_playlist_item(self):
        pipeline = self.get_pipeline()
        video_selector = self.get_pipeline().get_by_name("video_selector")
        audio_selector = self.get_pipeline().get_by_name("audio_selector")
        pipeline.set_state(Gst.State.READY)
        if self.data.playlist[self.data.index].type == "html":
            sink = self.get_html_sink()
        else:
            sink = "sink_0"
            uridecodebin = self.get_pipeline().get_by_name("uridecodebin")
            uridecodebin.set_property("uri", self.data.playlist[self.data.index].uri)
            uridecodebin.set_state(Gst.State.PLAYING)
        print(f"Set active sink -> {sink}")
        video_selector.set_property("active-pad", self.get_selector_pad("video", sink))
        audio_selector.set_property("active-pad", self.get_selector_pad("audio", sink))
        pipeline.set_state(Gst.State.PAUSED)

    def _on_eos(self, bus, msg):
        pipeline = self.get_pipeline()
        uridecodebin = pipeline.get_by_name("uridecodebin")
        active_pad = self.get_active_pad()
        active_pad_name = active_pad.get_name()
        self.set_playlist_item()

        pipeline.set_state(Gst.State.PLAYING)
        uridecodebin.set_state(Gst.State.PLAYING)
        self.data.current_clip = self.data.playlist[self.data.index].uri
        if active_pad_name == "sink_1" or active_pad_name == "sink_2":
            self.remove_pipeline(active_pad.get_peer().get_parent_element())
        if self.data.playlist[self.data.index].type == "html":
            # @TODO use asyncio // use duration property
            time.sleep(5)
            eos_event = Gst.Event.new_eos()
            pipeline.send_event(eos_event)

    def remove_pipeline(self, bin):
        bin.set_state(Gst.State.PAUSED)
        bin.set_state(Gst.State.READY)
        bin.set_state(Gst.State.NULL)
        for pad in bin.pads:
            peer = pad.get_peer()
            if peer:
                pad.unlink(peer)
        bin.set_state(Gst.State.NULL)
        self.get_pipeline().remove(bin)

    def print_pipeline_state(self):
        self.pipeline.set_state(Gst.State.PLAYING)
        return True

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

    def describe(self):

        return self.data
