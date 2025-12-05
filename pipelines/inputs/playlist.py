"""
Playlist input for playing sequences of video/HTML clips.

Fixed issues:
- Replaced blocking wait_until_buffer_empty() with non-blocking GLib timeout
- Replaced unbounded recursion in next_uri() with iteration
- Replaced daemon thread for HTML stop with GLib timer
- Added thread-safe locking for shared state access
"""

import requests
import threading
import os
import time
from typing import Optional

from api.inputs.playlist import PlaylistInputDTO, PlaylistItemDTO
from pipelines.inputs.input import Input
from gi.repository import Gst, GLib
from logger import logger


class PlaylistInput(Input):
    data: PlaylistInputDTO
    _state_lock: threading.Lock
    _html_stop_timer_id: Optional[int]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._state_lock = threading.Lock()
        self._html_stop_timer_id = None

    def build(self):
        pipeline = Gst.Pipeline.new("pipeline")
        uridecodebin = Gst.ElementFactory.make("uridecodebin3", "uridecodebin")
        self.data.index = -1
        uri = self.next_uri()

        if uri is None:
            logger.log("No valid URI found in playlist", level='ERROR')
            return

        uridecodebin.set_property('uri', uri)
        uridecodebin.set_property('buffer-duration', 6 * Gst.SECOND)
        uridecodebin.set_property('download', True)
        uridecodebin.set_property('use-buffering', True)
        uridecodebin.set_property('async-handling', True)
        uridecodebin.connect("pad-added", self.on_pad_added)
        pipeline.add(uridecodebin)

        videobin = Gst.parse_bin_from_description(f"{self.get_video_end()}", True)
        videobin.set_name("videobin")
        pipeline.add(videobin)
        videobin.sync_state_with_parent()

        audiobin = Gst.parse_bin_from_description(
            f"audiotestsrc wave=4 ! audioconvert ! audiorate ! audioresample ! "
            f"audiomixer name=audiomixer ! audioresample ! {self.get_audio_end()}",
            True
        )
        audiobin.set_name("audiobin")
        pipeline.add(audiobin)
        audiobin.sync_state_with_parent()

        self.add_pipeline(pipeline)

        with self._state_lock:
            if self.data.playlist[self.data.index].type == "html":
                self.run_html_stop_task(self.data.playlist[self.data.index].duration)

    def run_html_stop_task(self, duration):
        """
        Schedule HTML content stop using GLib timeout instead of separate thread.

        This avoids creating new event loops and threads for each HTML clip.
        """
        # Cancel any existing timer
        if self._html_stop_timer_id is not None:
            GLib.source_remove(self._html_stop_timer_id)
            self._html_stop_timer_id = None

        # Schedule in GLib main loop (milliseconds)
        self._html_stop_timer_id = GLib.timeout_add(
            int(duration * 1000),
            self._on_html_duration_complete
        )
        self.data.duration = duration

    def _on_html_duration_complete(self):
        """GLib callback when HTML duration expires."""
        self._html_stop_timer_id = None
        self.send_eos_event()
        return False  # Don't repeat

    def on_pad_added(self, src, pad):
        pad_type = pad.query_caps(None).to_string()
        if "audio" in pad_type:
            if not pad.is_linked():
                audiobin = self.get_pipeline().get_by_name("audiobin")
                audiomixer = audiobin.get_by_name("audiomixer")
                self.get_mixer_pad(audiomixer)
                audiomixer_sink_pad_template = audiomixer.get_pad_template("sink_%u")
                audiomixer_sink_pad = audiomixer.request_pad(audiomixer_sink_pad_template, None, None)

                bin = Gst.parse_bin_from_description(
                    "queue ! audioconvert ! audiorate ! audioresample ! queue",
                    True
                )
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

    def send_eos_event(self):
        eos_event = Gst.Event.new_eos()
        uridecodebin = self.get_pipeline().get_by_name("uridecodebin")
        uridecodebin.send_event(eos_event)
        return False

    def add_duration(self):
        pipeline = self.get_pipeline().get_by_name("uridecodebin")
        duration = (pipeline.query_duration(Gst.Format.TIME).duration // Gst.SECOND)
        if duration and duration != -1:
            self.data.duration = duration

    def _load_playlist(self, uri):
        """Load playlist from URL with retry logic."""
        max_retries = 10
        for attempt in range(max_retries):
            try:
                r = requests.get(uri, timeout=10)
                if r.status_code == 200:
                    return r.json()
            except requests.exceptions.RequestException as e:
                logger.log(f"Error loading playlist (attempt {attempt + 1}): {e}", level='ERROR')
            time.sleep(0.1)
        return None

    def _jumpToNextPlaylist(self):
        """Jump to the next playlist in the chain. Returns True on success."""
        data = self._load_playlist(self.data.next)
        if data is None:
            logger.log(f"Failed to load next playlist: {self.data.next}", level='ERROR')
            return False

        if "playlist" not in data:
            logger.log(f"Invalid playlist format (missing 'playlist' key): {self.data.next}", level='ERROR')
            return False

        try:
            next_playlist = [PlaylistItemDTO(**item) for item in data["playlist"]]
            self.data.playlist = next_playlist
            self.data.next = data.get("next")
            self.data.looping = data.get("looping", False)
            self.data.total_duration = data.get("total_duration", 0)
            self.data.index = 0
            return True
        except Exception as e:
            logger.log(f"Error parsing playlist: {e}", level='ERROR')
            return False

    def next_uri(self):
        """
        Get the next valid URI from the playlist.

        Uses iteration instead of recursion to prevent stack overflow.
        Thread-safe access to shared state.
        """
        MAX_ATTEMPTS = len(self.data.playlist) * 2 + 10  # Reasonable limit

        for attempt in range(MAX_ATTEMPTS):
            with self._state_lock:
                self.data.index += 1

                if self.data.index >= len(self.data.playlist):
                    if self.data.next is not None:
                        if not self._jumpToNextPlaylist():
                            # Failed to load next playlist
                            if self.data.looping:
                                self.data.index = 0
                            else:
                                return None
                    elif self.data.looping:
                        self.data.index = 0
                    else:
                        # Playlist exhausted, no looping
                        logger.log("Playlist exhausted, no valid URI found", level='WARNING')
                        return None

                if self.data.index >= len(self.data.playlist):
                    logger.log("Playlist index out of bounds", level='ERROR')
                    return None

                item = self.data.playlist[self.data.index]
                uri = item.uri
                self.data.current_clip = uri

            # Validation outside the lock
            if item.type == "video":
                if uri.startswith("http"):
                    try:
                        response = requests.head(uri, timeout=5)
                        if response.status_code == 200:
                            return uri
                        else:
                            logger.log(f"HTTP check failed for {uri}: {response.status_code}", level='WARNING')
                            continue  # Try next item
                    except requests.RequestException as e:
                        logger.log(f"HTTP check error for {uri}: {e}", level='WARNING')
                        continue  # Try next item
                elif uri.startswith("file://"):
                    file_path = uri.replace("file://", "")
                    if os.path.isfile(file_path):
                        return uri
                    else:
                        logger.log(f"File not found: {file_path}", level='WARNING')
                        continue  # Try next item
                else:
                    # Other URI schemes, try them
                    return uri
            elif item.type == "html":
                return "web+" + uri
            else:
                logger.log(f"Unknown item type: {item.type}", level='WARNING')
                continue  # Try next item

        # Exhausted attempts
        logger.log(f"Could not find valid URI after {MAX_ATTEMPTS} attempts", level='ERROR')
        return None

    def change_uri(self):
        """Change to the next URI in the playlist."""
        uri = self.next_uri()
        if uri is None:
            logger.log("Playlist exhausted, no valid URI found", level='WARNING')
            return False

        uridecodebin = self.get_pipeline().get_by_name("uridecodebin")
        self.get_pipeline().set_state(Gst.State.READY)
        self.remove_bin()
        uridecodebin.set_property("uri", uri)
        self.get_pipeline().set_state(Gst.State.PLAYING)

        with self._state_lock:
            if self.data.playlist[self.data.index].type == "html":
                duration = self.data.playlist[self.data.index].duration
                self.run_html_stop_task(duration)

        return False  # For GLib.idle_add

    def on_event(self, pad, info):
        """
        Pad probe callback - MUST NOT BLOCK.

        Instead of blocking to wait for buffer empty, we use a non-blocking
        approach with GLib idle callbacks.
        """
        event = info.get_event()
        if event.type == Gst.EventType.EOS:
            # Schedule the check in GLib idle, don't block here
            GLib.idle_add(self._check_buffer_and_change_uri)
        return Gst.PadProbeReturn.OK

    def _check_buffer_and_change_uri(self):
        """
        Non-blocking buffer check. Reschedules itself if not ready.
        """
        pipeline = self.get_pipeline()
        uridecodebin = pipeline.get_by_name("uridecodebin")

        success_pos, position = pipeline.query_position(Gst.Format.TIME)
        success_dur, duration = uridecodebin.query_duration(Gst.Format.TIME)

        if success_pos and success_dur and position >= duration:
            # Buffer is empty, safe to change URI
            self.change_uri()
            return False  # Don't repeat
        else:
            # Not ready yet, check again in 10ms
            GLib.timeout_add(10, self._check_buffer_and_change_uri)
            return False  # Current callback done

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

    def get_mixer_pad(self, element):
        if element is None:
            return None
        iterator = element.iterate_pads()
        while True:
            result, pad = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            if pad.get_name() != "src" and pad.get_name() != "sink_0":
                return pad.get_name()
        return None

    def describe(self):
        return self.data
