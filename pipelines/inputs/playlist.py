"""Playlist input for sequences of video/HTML clips. Extends Uridecodebin3Input with a wpesrc HTML path into the compositor."""

import httpx
import threading
import time
from typing import Optional

from api.inputs.playlist import PlaylistInputDTO, PlaylistItemDTO
from pipelines.inputs.uridecodebin3 import Uridecodebin3Input
from gi.repository import Gst, GLib
from logger import logger
from event_loop_bridge import safe_broadcast

_USE_CEF = None

def _check_cef():
    global _USE_CEF
    if _USE_CEF is None:
        _USE_CEF = bool(Gst.ElementFactory.find("cefsrc"))
    return _USE_CEF

DEFAULT_HTML_DURATION = 10  # seconds
TRANSITION_DELAY_MS = 200   # ms to wait before alpha swap (fallback when not prestarted)
PRESTART_SECS = 1           # seconds before clip end to prestart next source
CLIP_ERROR_TIMEOUT_MS = 10000  # ms to wait for pads before skipping clip
BUFFER_WATCHDOG_MS = 5000   # ms without video buffer before skipping clip


class PlaylistInput(Uridecodebin3Input):
    data: PlaylistInputDTO
    _state_lock: threading.Lock
    _html_stop_timer_id: Optional[int]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._state_lock = threading.Lock()
        self._html_stop_timer_id = None
        self._html_position_timer_id = None
        self._html_start_time = None
        self._prefetched_next = None
        self._changing_clip = False
        self._changing_flag_timer_id = None
        self._error_suppress_timer_id = None
        self._swap_timer_id = None
        self._html_active = False
        self._htmlsrc = None
        self._cefdemux = None
        self._html_audiosrc = None
        self._preloaded_html_uri = None
        self._prestarted_video_uri = None
        self._wpe_ready = True  # True when wpesrc chain is idle/ready for use
        self._pending_stop_html = False
        self._loading_next_playlist = False
        self._clip_error_timer_id = None
        self._pending_html_duration = None
        self._suppress_teardown_error = False
        self._watchdog_timer_id = None
        self._watchdog_probe_id = None
        self._pending_advance = False

    def cleanup(self):
        """Cancel all active timers and probes — call before deletion."""
        for attr in ('_html_stop_timer_id', '_html_position_timer_id',
                     '_changing_flag_timer_id', '_error_suppress_timer_id',
                     '_swap_timer_id', '_clip_error_timer_id', '_watchdog_timer_id'):
            tid = getattr(self, attr, None)
            if tid is not None:
                try:
                    GLib.source_remove(tid)
                except Exception:
                    pass
                setattr(self, attr, None)
        # Remove watchdog buffer probe
        if self._watchdog_probe_id and self.video_tee:
            try:
                src_pad = self.video_tee.get_static_pad("src_0")
                if src_pad:
                    src_pad.remove_probe(self._watchdog_probe_id)
            except Exception:
                pass
            self._watchdog_probe_id = None
        # NULL wpesrc on deletion — safe here (one-time, not cycling)
        # This frees the WebKit renderer process (~250MB)
        for chain in (getattr(self, '_wpe_chain', []), getattr(self, '_html_audio_chain', [])):
            for elem in reversed(chain):
                elem.set_state(Gst.State.NULL)

    def _get_source_uri(self):
        """Return first clip URI from playlist."""
        self.data.index = -1
        if not self.data.total_duration:
            self.data.total_duration = self._sum_clip_durations()
        item_type, uri = self._next_clip()
        if uri is None:
            self.data.state = "EOS"
            return ""
        self._update_clip_metadata()
        if item_type == "html":
            self._first_html = (uri, self.data.playlist[self.data.index].duration)
            return ""
        return uri

    def build_bin(self) -> Gst.Bin:
        """Build bin with wpesrc chain for HTML clips, attached to the parent's compositor/audiomixer."""
        container = super().build_bin()
        # Playlist follows global config (not pad detection like uridecodebin3)
        from config_handler import ConfigReader
        self.data.has_video = ConfigReader().get_enable_video()
        self.data.has_audio = ConfigReader().get_enable_audio()
        uid = self.data.uid
        video_caps = self.get_caps('video')

        # === HTML source: always wpesrc for playlist (cefsrc crashes on NULL→PLAYING cycle) ===
        # Start on about:blank — navigate in place for each clip (never NULL, avoids segfault)
        self._htmlsrc = Gst.ElementFactory.make("wpesrc", f"wpesrc_{uid}")
        self._htmlsrc.set_property("location", "about:blank")
        self._htmlsrc.set_property("draw-background", True)
        self._cefdemux = None

        wpe_vconv = Gst.ElementFactory.make("videoconvert", f"wpe_vconv_{uid}")
        wpe_vscale = Gst.ElementFactory.make("videoscale", f"wpe_vscale_{uid}")
        wpe_vrate = Gst.ElementFactory.make("videorate", f"wpe_vrate_{uid}")
        wpe_vrate.set_property("skip-to-first", True)
        wpe_vcaps = Gst.ElementFactory.make("capsfilter", f"wpe_vcaps_{uid}")
        wpe_vcaps.set_property("caps", Gst.Caps.from_string(video_caps))
        wpe_vqueue = Gst.ElementFactory.make("queue", f"wpe_vqueue_{uid}")
        wpe_vqueue.set_property("leaky", 2)
        wpe_vqueue.set_property("max-size-buffers", 1)
        wpe_vqueue.set_property("max-size-bytes", 0)
        wpe_vqueue.set_property("max-size-time", 0)

        # Silence source for HTML clips
        self._html_audiosrc = Gst.ElementFactory.make("audiotestsrc", f"html_audiosrc_{uid}")
        self._html_audiosrc.set_property("wave", 4)
        self._html_audiosrc.set_property("do-timestamp", True)
        self._html_audiosrc.set_property("is-live", True)
        html_acaps = Gst.ElementFactory.make("capsfilter", f"html_acaps_{uid}")
        html_acaps.set_property("caps", Gst.Caps.from_string(self.get_caps('audio')))
        html_aconv = Gst.ElementFactory.make("audioconvert", f"html_aconv_{uid}")
        html_aresample = Gst.ElementFactory.make("audioresample", f"html_aresample_{uid}")
        html_aqueue = Gst.ElementFactory.make("queue", f"html_aqueue_{uid}")
        html_aqueue.set_property("leaky", 2)
        html_aqueue.set_property("max-size-buffers", 1)
        html_aqueue.set_property("max-size-bytes", 0)
        html_aqueue.set_property("max-size-time", 0)

        html_elems = [self._htmlsrc, wpe_vconv, wpe_vscale, wpe_vrate, wpe_vcaps, wpe_vqueue,
                     self._html_audiosrc, html_acaps, html_aconv, html_aresample, html_aqueue]
        for elem in html_elems:
            container.add(elem)

        # Link wpesrc video chain → compositor
        self._htmlsrc.get_static_pad("video").link(wpe_vconv.get_static_pad("sink"))
        wpe_vconv.link(wpe_vscale)
        wpe_vscale.link(wpe_vrate)
        wpe_vrate.link(wpe_vcaps)
        wpe_vcaps.link(wpe_vqueue)
        wpe_vqueue.link(self.input_videomixer)
        self._wpe_comp_pad = wpe_vqueue.get_static_pad("src").get_peer()
        if self._wpe_comp_pad:
            self._wpe_comp_pad.set_property("alpha", 0.0)

        # Link html audio chain → audiomixer (parent's input_audiomixer)
        self._html_audiosrc.link(html_acaps)
        html_acaps.link(html_aconv)
        html_aconv.link(html_aresample)
        html_aresample.link(html_aqueue)
        html_aqueue.link(self.input_audiomixer)

        self._wpe_chain = [self._htmlsrc, wpe_vconv, wpe_vscale, wpe_vrate, wpe_vcaps, wpe_vqueue]
        self._html_audio_chain = [self._html_audiosrc, html_acaps, html_aconv, html_aresample, html_aqueue]

        # Lock audio chain (silent until HTML clip active)
        # Video chain stays unlocked — wpesrc runs on about:blank at alpha=0 (negligible cost)
        for elem in self._html_audio_chain:
            elem.set_locked_state(True)

        # If first clip is HTML, lock uridecodebin and schedule switch
        if hasattr(self, '_first_html'):
            self.uridecodebin.set_locked_state(True)
            uri, duration = self._first_html
            del self._first_html
            GLib.timeout_add(500, self._switch_first_html, uri, duration)

        return container

    def _switch_first_html(self, uri, duration):
        try:
            self._switch_to_html(uri, duration)
            safe_broadcast("UPDATE", self.data)
        except Exception as e:
            logger.log(f"Exception in _switch_first_html: {e}", level='ERROR')
        return False

    async def update(self, data):
        from api.input_models import updateInputDTO
        if not isinstance(data, updateInputDTO):
            data = updateInputDTO.model_validate(data)
        if data.skip and self.data.state != 'PLAYING':
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail="Skip requires playlist to be PLAYING. Resume first.")
        if data.skip == "next":
            GLib.idle_add(self._skip_next)
        elif data.skip == "previous":
            GLib.idle_add(self._skip_previous)
        if data.state == 'PAUSED':
            GLib.idle_add(self._pause_html_timers)
        elif data.state == 'PLAYING' and self.data.state == 'PAUSED':
            GLib.idle_add(self._resume_html_timers)
        await super().update(data)

    def _pause_html_timers(self):
        """Pause HTML timers, saving elapsed time for resume."""
        if self._html_active and self._html_start_time is not None:
            self._html_paused_elapsed = time.monotonic() - self._html_start_time
        for attr in ('_html_stop_timer_id', '_html_position_timer_id', '_swap_timer_id'):
            tid = getattr(self, attr, None)
            if tid is not None:
                GLib.source_remove(tid)
                setattr(self, attr, None)
        return False

    def _resume_html_timers(self):
        """Resume HTML duration timer with remaining time after unpause."""
        if not self._html_active or not hasattr(self, '_html_paused_elapsed'):
            if self._pending_advance:
                self._pending_advance = False
                GLib.idle_add(self._change_clip)
            return False
        elapsed = self._html_paused_elapsed
        del self._html_paused_elapsed
        remaining = (self.data.duration or 0) - elapsed
        if remaining <= 0:
            self._on_html_duration_complete()
            return False
        self._html_start_time = time.monotonic() - elapsed
        self._html_stop_timer_id = GLib.timeout_add(
            int(remaining * 1000), self._on_html_duration_complete)
        self._html_position_timer_id = GLib.timeout_add(1000, self._update_html_position)
        if self._pending_advance:
            self._pending_advance = False
            GLib.idle_add(self._change_clip)
        return False

    def _skip_next(self):
        """Skip to next clip."""
        if self._changing_clip:
            return False
        self._changing_clip = True
        self._change_clip()
        return False

    def _skip_previous(self):
        """Skip to previous clip."""
        if self._changing_clip:
            return False
        self._changing_clip = True
        self.data.index = max(self.data.index - 2, -1)
        self._change_clip()
        return False

    def handle_eos(self) -> bool:
        """Handle EOS — advance to next clip. Always returns True."""
        if self.data.state == 'PAUSED':
            self._pending_advance = True
            return True
        if self._changing_clip:
            return True
        self._changing_clip = True
        logger.log(f"Playlist {self.data.uid} advancing to next clip", level='DEBUG')
        GLib.idle_add(self._change_clip)
        return True

    # --- Chain flush (for video-to-video transitions) ---

    def _flush_chain(self):
        """Flush vqueue→clocksync and aqueue→aclocksync without disrupting downstream."""
        for (q, cs) in [(self._vqueue, self._vclocksync),
                        (self._aqueue, self._aclocksync)]:
            src = cs.get_static_pad("src")
            probe_id = src.add_probe(
                Gst.PadProbeType.EVENT_DOWNSTREAM | Gst.PadProbeType.EVENT_FLUSH,
                lambda p, i, d: Gst.PadProbeReturn.DROP, None)
            sink = q.get_static_pad("sink")
            sink.send_event(Gst.Event.new_flush_start())
            sink.send_event(Gst.Event.new_flush_stop(True))
            src.remove_probe(probe_id)

    def _reset_changing_flag(self):
        self._changing_flag_timer_id = None
        self._changing_clip = False
        return False

    def _clear_error_suppress(self):
        self._error_suppress_timer_id = None
        self._suppress_teardown_error = False
        return False

    def _cancel_clip_error_timer(self):
        if self._clip_error_timer_id is not None:
            GLib.source_remove(self._clip_error_timer_id)
            self._clip_error_timer_id = None

    def _on_clip_error_timeout(self):
        """Skip to next clip when current clip fails to produce pads."""
        try:
            self._clip_error_timer_id = None
            if self.data.state == 'PAUSED':
                return False
            if self._video_linked[0]:
                return False  # Pads appeared, no error
            uri = self.uridecodebin.get_property("uri") if self.uridecodebin else "?"
            logger.log(f"Playlist {self.data.uid} clip failed (no pads): {uri}", level='ERROR')
            self._suppress_teardown_error = False
            self._changing_clip = False
            self.handle_eos()  # Skip to next clip
        except Exception as e:
            logger.log(f"Exception in _on_clip_error_timeout: {e}", level='ERROR')
        return False

    # --- Buffer watchdog (skip frozen clips) ---

    def _start_watchdog(self):
        """Start buffer flow watchdog for video clips."""
        self._stop_watchdog()
        # Install buffer probe on video tee src pad
        if self.video_tee:
            src_pad = self.video_tee.get_static_pad("src_0")
            if src_pad:
                self._watchdog_probe_id = src_pad.add_probe(
                    Gst.PadProbeType.BUFFER, self._watchdog_buffer_probe, None)
        self._reset_watchdog()

    def _stop_watchdog(self):
        """Stop buffer watchdog."""
        if self._watchdog_timer_id is not None:
            GLib.source_remove(self._watchdog_timer_id)
            self._watchdog_timer_id = None
        if self._watchdog_probe_id is not None and self.video_tee:
            src_pad = self.video_tee.get_static_pad("src_0")
            if src_pad:
                src_pad.remove_probe(self._watchdog_probe_id)
            self._watchdog_probe_id = None

    def _reset_watchdog(self):
        """Reset watchdog timer — called on every buffer.
        Must run on GLib main thread (uses GLib.source_remove/timeout_add)."""
        if self._watchdog_timer_id is not None:
            GLib.source_remove(self._watchdog_timer_id)
        self._watchdog_timer_id = GLib.timeout_add(
            BUFFER_WATCHDOG_MS, self._on_watchdog_timeout)
        return False

    def _watchdog_buffer_probe(self, pad, info, user_data):
        """Pad probe: schedule watchdog reset on GLib main thread.
        Pad probes run on streaming threads — GLib timer ops are not thread-safe."""
        GLib.idle_add(self._reset_watchdog)
        return Gst.PadProbeReturn.OK

    def _on_watchdog_timeout(self):
        """No video buffer for BUFFER_WATCHDOG_MS — skip to next clip."""
        try:
            self._watchdog_timer_id = None
            if self.data.state == 'PAUSED':
                return False
            if self._html_active or self._changing_clip:
                return False
            uri = self.uridecodebin.get_property("uri") if self.uridecodebin else "?"
            logger.log(f"Playlist {self.data.uid} clip frozen (no buffers): {uri}", level='WARNING')
            self._changing_clip = False
            self.handle_eos()
        except Exception as e:
            logger.log(f"Exception in _on_watchdog_timeout: {e}", level='ERROR')
        return False

    # --- Bus error recovery ---

    def handle_error(self, err_message):
        """Called by core_pipeline on bus error. Skip to next clip."""
        if self.data.state == 'PAUSED':
            self._pending_advance = True
            return
        if self._changing_clip:
            return
        logger.log(f"Playlist {self.data.uid} clip error, skipping: {err_message}", level='WARNING')
        self._changing_clip = False
        self.handle_eos()

    # --- Clip transitions ---

    def _change_clip(self):
        """Switch to next clip. Runs in GLib main loop."""
        uid = self.data.uid

        # Cancel any lingering timers from previous clip
        self._stop_watchdog()
        for attr in ('_html_stop_timer_id', '_html_position_timer_id',
                     '_changing_flag_timer_id', '_error_suppress_timer_id', '_swap_timer_id'):
            tid = getattr(self, attr, None)
            if tid is not None:
                GLib.source_remove(tid)
                setattr(self, attr, None)
        self._html_start_time = None

        item_type, new_uri = self._next_clip()
        logger.log(f"Playlist {uid} _change_clip: type={item_type} uri={new_uri[:80] if new_uri else None} idx={self.data.index}", level='DEBUG')
        if not new_uri:
            if self._loading_next_playlist:
                # Async playlist load in progress — will retry when done
                return False
            self._changing_clip = False
            self.data.state = "EOS"
            safe_broadcast("UPDATE", self.data)
            logger.log(f"Playlist {uid} exhausted", level='DEBUG')
            return False

        if self.data.index >= len(self.data.playlist):
            self._changing_clip = False
            return False
        item = self.data.playlist[self.data.index]
        logger.log(f"Playlist {uid} clip {self.data.index} ({item_type}): {new_uri}", level='DEBUG')

        # Reset position for new clip
        self.data.position = 0
        self.data.duration = 0
        self._update_clip_metadata()

        if item_type == "html":
            self._stop_watchdog()
            self._switch_to_html(new_uri, item.duration)
        else:
            self._switch_to_video(new_uri)
            self._start_watchdog()

        # Keep _changing_clip=True briefly to absorb the stale video/audio EOS
        self._changing_flag_timer_id = GLib.timeout_add(500, self._reset_changing_flag)
        safe_broadcast("UPDATE", self.data)

        self._maybe_prefetch_next()
        return False

    def _switch_to_video(self, uri):
        """Switch to a video clip via uridecodebin3."""
        if self._prestarted_video_uri == uri:
            # Video already prerolled at alpha=0 — refresh offsets and go
            logger.log(f"Using prestarted video for {uri}", level='DEBUG')
            self._prestarted_video_uri = None
            self._cancel_clip_error_timer()
            self._update_pad_offsets()
            self.uridecodebin.set_locked_state(False)
            self.uridecodebin.set_state(Gst.State.PLAYING)
            self._swap_to_video()
            return

        # Defer _stop_html until new video pad links (avoids stale frame flash)
        if self._html_active:
            self._pending_stop_html = True

        self._video_linked[0] = False
        self._audio_linked[0] = False
        self._suppress_teardown_error = True

        # Unlink old uridecodebin pads from queues before NULL
        for q in (self._vqueue, self._aqueue):
            sink = q.get_static_pad("sink")
            peer = sink.get_peer()
            if peer:
                peer.unlink(sink)

        # Flush downstream chain to reset videorate/clocksync state.
        # Without this, the 2nd clip stalls for the 1st clip's duration.
        self._flush_chain()

        # Cold restart: NULL → set URI → PLAYING
        self.uridecodebin.set_locked_state(True)
        self.uridecodebin.set_state(Gst.State.NULL)
        self.uridecodebin.set_property("uri", uri)
        self.uridecodebin.set_locked_state(False)
        self.uridecodebin.set_state(Gst.State.PLAYING)
        logger.log(f"Playlist {self.data.uid} cold start: {uri}", level='DEBUG')

        self._error_suppress_timer_id = GLib.timeout_add(2000, self._clear_error_suppress)
        # Skip to next clip if this one fails to produce pads
        self._cancel_clip_error_timer()
        self._clip_error_timer_id = GLib.timeout_add(
            CLIP_ERROR_TIMEOUT_MS, self._on_clip_error_timeout)

    def _switch_to_html(self, uri, duration):
        """Switch to an HTML clip via wpesrc (separate compositor path)."""
        # Cancel any video prestart
        if self._prestarted_video_uri:
            self._prestarted_video_uri = None

        if not self._html_active:
            # Stop uridecodebin3
            self._suppress_teardown_error = True
            self.uridecodebin.set_locked_state(True)
            self.uridecodebin.set_state(Gst.State.NULL)
            self._error_suppress_timer_id = GLib.timeout_add(2000, self._clear_error_suppress)

        self._pending_html_duration = duration
        prestarted = self._preloaded_html_uri == uri and self._wpe_ready

        if prestarted:
            # wpesrc already rendering frames — start audio and swap immediately
            logger.log(f"Using prestarted wpesrc for {uri}", level='DEBUG')
            for elem in self._html_audio_chain:
                elem.set_locked_state(False)
                elem.set_state(Gst.State.PLAYING)
            self._html_active = True
            self._preloaded_html_uri = None
            self._swap_to_html()
        else:
            # Cold start — need delay for wpesrc to render first frame
            logger.log(f"Cold-starting wpesrc for {uri}", level='DEBUG')
            for elem in self._wpe_chain:
                elem.set_locked_state(True)
            self._wpe_ready = False
            self._navigate_wpe(uri, start_audio=True)
            self._html_active = True
            self._preloaded_html_uri = None
            self._swap_timer_id = GLib.timeout_add(TRANSITION_DELAY_MS, self._swap_to_html)

    def _swap_to_html(self):
        """Show wpesrc, hide video, start HTML duration timer."""
        self._swap_timer_id = None
        if not self._html_active:
            return False
        if self._wpe_comp_pad:
            self._wpe_comp_pad.set_property("alpha", 1.0)
        real_vpad = getattr(self, '_real_video_pad', None)
        if real_vpad:
            real_vpad.set_property("alpha", 0.0)
        dur = self._pending_html_duration
        if dur and dur > 0:
            self.run_html_stop_task(dur)
        else:
            self.run_html_stop_task(DEFAULT_HTML_DURATION)
        return False

    def _stop_html(self):
        """Stop HTML — navigate to about:blank and pause chains (avoids segfault + saves CPU)."""
        if self._wpe_comp_pad:
            self._wpe_comp_pad.set_property("alpha", 0.0)
        self._htmlsrc.set_property("location", "about:blank")
        # Pause both video and audio chains to stop rendering invisible frames
        for elem in self._wpe_chain + self._html_audio_chain:
            elem.set_locked_state(True)
            elem.set_state(Gst.State.PAUSED)
        self._html_active = False
        self._wpe_ready = True

    def _navigate_wpe(self, uri, start_audio=False):
        """Navigate wpesrc to new URI without state cycling (avoids NULL→PLAYING segfault)."""
        def do_navigate():
            # Unpause video chain (paused during _stop_html)
            for elem in self._wpe_chain:
                elem.set_locked_state(False)
                elem.set_state(Gst.State.PLAYING)
            self._htmlsrc.set_property("location", uri)
            if start_audio:
                for elem in self._html_audio_chain:
                    elem.set_locked_state(False)
                    elem.set_state(Gst.State.PLAYING)
            self._wpe_ready = True
            return False
        GLib.idle_add(do_navigate)

    # --- HTML pre-start (start wpesrc before current clip ends) ---

    def _maybe_prestart_next_html(self):
        """If near end of current video clip and next is HTML, prestart wpesrc."""
        if self._html_active or self._preloaded_html_uri is not None:
            return
        if not self.data.duration or not self.data.position:
            return
        remaining = self.data.duration - self.data.position
        if remaining > PRESTART_SECS:
            return
        next_idx = self.data.index + 1
        if next_idx < len(self.data.playlist):
            item = self.data.playlist[next_idx]
            if item.type == "html":
                self._do_prestart_html(item.uri)

    def _do_prestart_html(self, uri):
        """Start wpesrc with URI at alpha=0 so it renders before transition."""
        if not self._wpe_ready:
            return
        logger.log(f"Pre-starting HTML: {uri}", level='DEBUG')
        for elem in self._wpe_chain:
            elem.set_locked_state(True)
        self._wpe_ready = False
        self._navigate_wpe(uri)
        self._preloaded_html_uri = uri

    # --- Video pre-start (preroll uridecodebin3 before HTML ends) ---

    def _maybe_prestart_next_video(self):
        """If near end of HTML clip and next is video, preroll uridecodebin3."""
        if not self._html_active or self._prestarted_video_uri is not None:
            return
        if self._html_start_time is None or not self.data.duration:
            return
        elapsed = int(time.monotonic() - self._html_start_time)
        remaining = self.data.duration - elapsed
        if remaining > PRESTART_SECS:
            return
        next_idx = self.data.index + 1
        if next_idx < len(self.data.playlist):
            item = self.data.playlist[next_idx]
            if item.type == "video":
                uri = item.uri
                self._do_prestart_video(uri)

    def _do_prestart_video(self, uri):
        """Start uridecodebin3 in PAUSED (preroll) so first frame is ready."""
        logger.log(f"Pre-starting video (PAUSED): {uri}", level='DEBUG')
        self._flush_chain()
        self._video_linked[0] = False
        self._audio_linked[0] = False
        self._suppress_teardown_error = True
        self.uridecodebin.set_locked_state(True)
        self.uridecodebin.set_state(Gst.State.NULL)
        self.uridecodebin.set_property("uri", uri)
        self.uridecodebin.set_state(Gst.State.PAUSED)
        self._error_suppress_timer_id = GLib.timeout_add(2000, self._clear_error_suppress)
        self._prestarted_video_uri = uri

    # --- HTML clip duration ---

    def run_html_stop_task(self, duration):
        if self._html_stop_timer_id is not None:
            GLib.source_remove(self._html_stop_timer_id)
            self._html_stop_timer_id = None
        if self._html_position_timer_id is not None:
            GLib.source_remove(self._html_position_timer_id)
            self._html_position_timer_id = None
        self._html_stop_timer_id = GLib.timeout_add(
            int(duration * 1000), self._on_html_duration_complete)
        self.data.duration = duration
        self.data.position = 0
        self._html_start_time = time.monotonic()
        self._html_position_timer_id = GLib.timeout_add(1000, self._update_html_position)

    def _update_html_position(self):
        try:
            if not self._html_active or self._html_start_time is None:
                self._html_position_timer_id = None
                return False
            elapsed = int(time.monotonic() - self._html_start_time)
            self.data.position = elapsed
            self._compute_total_position()
            safe_broadcast("UPDATE", self.data)
            self._maybe_prestart_next_video()
            return True  # repeat
        except Exception as e:
            logger.log(f"Exception in _update_html_position: {e}", level='ERROR')
            self._html_position_timer_id = None
            return False

    def _on_html_duration_complete(self):
        try:
            self._html_stop_timer_id = None
            if self._html_position_timer_id is not None:
                GLib.source_remove(self._html_position_timer_id)
                self._html_position_timer_id = None
            self._html_start_time = None
            logger.log(f"HTML duration expired for {self.data.uid}", level='DEBUG')
            self.handle_eos()
        except Exception as e:
            logger.log(f"Exception in _on_html_duration_complete: {e}", level='ERROR')
        return False

    # --- Playlist traversal ---

    def _next_clip(self):
        """Get next clip. Returns (type, uri) or (None, None)."""
        MAX_ATTEMPTS = max(len(self.data.playlist) * 2 + 10, 10) if self.data.playlist else 10

        for attempt in range(MAX_ATTEMPTS):
            with self._state_lock:
                self.data.index += 1

                if self.data.index >= len(self.data.playlist):
                    if self.data.next is not None:
                        if not self._jumpToNextPlaylist():
                            if self._loading_next_playlist:
                                return None, None
                            if self.data.looping:
                                self.data.index = 0
                            else:
                                return None, None
                    elif self.data.looping:
                        self.data.index = 0
                    else:
                        return None, None

                if self.data.index >= len(self.data.playlist):
                    return None, None

                item = self.data.playlist[self.data.index]
                uri = item.uri
                self.data.current_clip = item

            if item.type == "video":
                # Let uridecodebin3 handle all URIs (file/HTTP/SRT/RTMP).
                # No os.path.isfile() — it blocks GLib thread on network storage.
                # Missing files are caught by uridecodebin3 error → handle_error → skip.
                return "video", uri
            elif item.type == "html":
                return "html", uri
            else:
                logger.log(f"Unknown type: {item.type}", level='WARNING')
                continue

        return None, None

    # --- Playlist chaining ---

    def _jumpToNextPlaylist(self):
        # No lock here — called from _next_clip which already holds _state_lock
        data = self._prefetched_next
        self._prefetched_next = None
        if data is None:
            if self._changing_clip:
                # Runtime: async load to avoid blocking GLib thread
                self._loading_next_playlist = True
                self._start_async_playlist_load(self.data.next)
                return False
            # Init: sync load OK — GLib loop not running yet
            if self.data.next:
                data = self._load_playlist(self.data.next)
        return self._apply_playlist_data(data)

    def _apply_playlist_data(self, data):
        """Apply loaded playlist data. Returns True on success."""
        if data is None or "playlist" not in data:
            return False
        try:
            self.data.playlist = [PlaylistItemDTO(**item) for item in data["playlist"]]
            self.data.next = data.get("next")
            self.data.looping = data.get("looping", False)
            self.data.total_duration = data.get("total_duration") or self._sum_clip_durations()
            self.data.index = 0
            return True
        except Exception as e:
            logger.log(f"Error parsing playlist: {e}", level='ERROR')
            return False

    def _load_playlist(self, uri):
        """Load playlist JSON. Called from background threads only."""
        for attempt in range(3):
            try:
                r = httpx.get(uri, timeout=3, follow_redirects=True)
                if r.status_code == 200:
                    return r.json()
            except httpx.HTTPError as e:
                logger.log(f"Playlist load error (attempt {attempt + 1}): {e}", level='ERROR')
            if attempt < 2:
                time.sleep(0.5)
        return None

    # --- Pre-fetching next playlist ---

    def _maybe_prefetch_next(self):
        if (self.data.next and not self._prefetched_next and
                self.data.index == len(self.data.playlist) - 1):
            threading.Thread(target=self._do_prefetch, daemon=True).start()

    def _do_prefetch(self):
        data = self._load_playlist(self.data.next)
        if data and "playlist" in data:
            with self._state_lock:
                self._prefetched_next = data

    def _start_async_playlist_load(self, uri):
        """Load next playlist in background thread, resume on GLib thread."""
        def _load_and_resume():
            data = self._load_playlist(uri)
            if data and "playlist" in data:
                with self._state_lock:
                    self._prefetched_next = data
            GLib.idle_add(self._on_async_playlist_loaded)
        threading.Thread(target=_load_and_resume, daemon=True).start()

    def _on_async_playlist_loaded(self):
        """Resume clip change after async playlist load."""
        self._loading_next_playlist = False
        with self._state_lock:
            data = self._prefetched_next
            self._prefetched_next = None
        if data and self._apply_playlist_data(data):
            # _apply_playlist_data sets index=0; _next_clip will +1, so set to -1
            self.data.index = -1
            logger.log(f"Playlist {self.data.uid}: async load OK, {len(self.data.playlist)} clips, resuming", level='DEBUG')
            self._change_clip()
        elif self.data.playlist:
            # Next playlist failed — loop current playlist
            self.data.index = -1
            self.data.name = self.data.name.removesuffix(" (loop)") + " (loop)"
            logger.log(f"Playlist {self.data.uid}: next load failed, looping current playlist", level='WARNING')
            safe_broadcast("UPDATE", self.data)
            self._change_clip()
        else:
            self._changing_clip = False
            self.data.state = "EOS"
            self.data.details = "Failed to load next playlist"
            safe_broadcast("UPDATE", self.data)
            logger.log(f"Playlist {self.data.uid}: async playlist load failed, no clips to loop", level='ERROR')
        return False

    def _on_video_pad_linked(self):
        """Hide HTML overlay once new video starts flowing."""
        self._cancel_clip_error_timer()
        if self._pending_stop_html:
            self._pending_stop_html = False
            self._swap_timer_id = GLib.timeout_add(TRANSITION_DELAY_MS, self._swap_to_video)

    def _swap_to_video(self):
        """Show video, hide wpesrc."""
        self._swap_timer_id = None
        real_vpad = getattr(self, '_real_video_pad', None)
        if real_vpad:
            real_vpad.set_property("alpha", 1.0)
        self._stop_html()
        return False

    # --- Position tracking ---

    def _update_clip_metadata(self):
        """Update current_clip and details when clip changes."""
        if self.data.index < len(self.data.playlist):
            item = self.data.playlist[self.data.index]
            self.data.current_clip = item
            self.data.details = item.name or item.uri.rsplit('/', 1)[-1]

    def _sum_clip_durations(self):
        """Sum durations of all clips in the playlist."""
        total = 0
        for item in (self.data.playlist or []):
            if item.duration:
                total += item.duration
        return total

    def _compute_total_position(self):
        """Compute cumulative position across all played clips."""
        elapsed = 0
        for i in range(self.data.index):
            if i < len(self.data.playlist):
                item = self.data.playlist[i]
                if item.duration:
                    elapsed += item.duration
        self.data.total_position = elapsed + (self.data.position or 0)

    def on_position_updated(self):
        """Called by pipeline_handler after position update for video clips."""
        self._compute_total_position()
        self._maybe_prestart_next_html()

    def get_pipeline(self):
        """Return queryable element for position/duration.
        Returns None during HTML clips (position tracked via monotonic timer)."""
        if self._html_active:
            return None
        return self.uridecodebin
