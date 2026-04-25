from api.inputs.uridecodebin3 import Uridecodebin3InputDTO
from gi.repository import Gst, GLib, GObject
from logger import logger
from event_loop_bridge import safe_broadcast
from config_handler import ConfigReader

from pipelines.inputs.input import Input


_LIVE_SCHEMES = frozenset(("srt", "rtmp", "rtsp", "rtsps", "udp", "rtp", "rtsp+tcp"))
# Protocols with their own jitter/retransmission buffers — no GStreamer buffering needed
_SELF_BUFFERED_SCHEMES = frozenset(("srt", "udp", "rtp"))


def _is_live_uri(uri: str) -> bool:
    """Return True if the URI scheme indicates a live source."""
    if not uri:
        return False
    scheme = uri.split("://", 1)[0].lower() if "://" in uri else ""
    return scheme in _LIVE_SCHEMES


def _is_self_buffered_uri(uri: str) -> bool:
    """Return True if the protocol handles its own buffering (SRT, UDP, RTP)."""
    if not uri:
        return False
    scheme = uri.split("://", 1)[0].lower() if "://" in uri else ""
    return scheme in _SELF_BUFFERED_SCHEMES


class Uridecodebin3Input(Input):
    data: Uridecodebin3InputDTO
    uridecodebin: Gst.Element = None
    input_videomixer: Gst.Element = None
    input_audiomixer: Gst.Element = None
    _is_live: bool = False

    def build_pipeline_str(self) -> str:
        """Not used - this input uses build_bin() instead."""
        raise NotImplementedError("Uridecodebin3Input uses build_bin()")

    def _get_source_uri(self):
        """Return URI for the source element. Override for URL resolution (e.g. yt-dlp)."""
        return self.data.uri

    def build_bin(self) -> Gst.Bin:
        """Build a bin containing uridecodebin3 with video/audio processing chains.

        Both video and audio use per-input aggregator barriers (compositor/audiomixer)
        with force-live fallback sources. These absorb FLUSH from seek/loop so
        downstream (tee consumers, scene mixer) never sees discontinuity.
        """
        uid = self.data.uid
        uri = self._get_source_uri()

        # Source is unknown until pads arrive — override DTO defaults
        self.data.has_video = False
        self.data.has_audio = False

        container = Gst.Bin.new(f"input_bin_{uid}")
        container.set_property("async-handling", True)
        self._video_event_probe_id = None
        self._video_event_probe_pad = None
        self._audio_event_probe_id = None
        self._audio_event_probe_pad = None

        # --- Source ---
        self._is_live = _is_live_uri(uri)
        uridecodebin = Gst.ElementFactory.make("uridecodebin3", f"uridecodebin_{uid}")
        if uri:
            uridecodebin.set_property("uri", uri)
        if _is_self_buffered_uri(uri):
            # SRT/UDP/RTP: protocol handles buffering, disable GStreamer's
            uridecodebin.set_property("buffer-size", 0)
            uridecodebin.set_property("buffer-duration", 0)
            uridecodebin.set_property("use-buffering", False)
        elif self._is_live:
            # RTMP/RTSP: live but TCP-based, use small buffer with buffering messages
            uridecodebin.set_property("buffer-size", 262144)
            uridecodebin.set_property("buffer-duration", 500 * Gst.MSECOND)
            uridecodebin.set_property("use-buffering", True)
        else:
            # Files/HTTP: normal buffering
            uridecodebin.set_property("buffer-size", 1048576)
            uridecodebin.set_property("buffer-duration", 2 * Gst.SECOND)
            uridecodebin.set_property("use-buffering", True)

        # --- Tees ---
        video_tee = Gst.ElementFactory.make("tee", f"video_tee_{uid}")
        video_tee.set_property("allow-not-linked", True)
        audio_tee = Gst.ElementFactory.make("tee", f"audio_tee_{uid}")
        audio_tee.set_property("allow-not-linked", True)

        # === VIDEO CHAIN ===
        vqueue = Gst.ElementFactory.make("queue", f"vqueue_{uid}")
        vqueue.set_property("max-size-time", 300000000)
        videoconvert = Gst.ElementFactory.make("videoconvert", f"videoconvert_{uid}")
        videoscale = Gst.ElementFactory.make("videoscale", f"videoscale_{uid}")
        videorate = Gst.ElementFactory.make("videorate", f"videorate_{uid}")
        videorate.set_property("skip-to-first", True)
        vcapsfilter = Gst.ElementFactory.make("capsfilter", f"vcapsfilter_{uid}")
        vcapsfilter.set_property("caps", Gst.Caps.from_string(self.get_caps('video')))
        vclocksync = Gst.ElementFactory.make("clocksync", f"vclocksync_{uid}")
        vclocksync.set_property("sync-to-first", True)

        # Per-input compositor (FLUSH barrier for video) — force-live is construct-only.
        # start_time_selection=1 (FIRST): compositor starts at fallback's running_time
        # (= pipeline clock). Without this, output running_time starts at 0 causing
        # a burst of catch-up frames → stuttering at start.
        _compositor_type = Gst.ElementFactory.find("compositor").get_element_type()
        input_videomixer = GObject.new(_compositor_type,
            name=f"input_videomixer_{uid}",
            force_live=True,
            latency=150000000,
            ignore_inactive_pads=True,
            background=1,
            start_time_selection=1)

        fallback_videosrc = Gst.ElementFactory.make("videotestsrc", f"fallback_videosrc_{uid}")
        fallback_videosrc.set_property("do-timestamp", True)
        fallback_videosrc.set_property("is-live", True)
        fallback_videosrc.set_property("pattern", 2)
        fallback_vcaps = Gst.ElementFactory.make("capsfilter", f"fallback_vcaps_{uid}")
        fallback_vcaps.set_property("caps", Gst.Caps.from_string(self.get_caps('video')))

        post_vrate = Gst.ElementFactory.make("videorate", f"post_vrate_{uid}")
        post_vrate.set_property("skip-to-first", True)
        post_vconv = Gst.ElementFactory.make("videoconvert", f"post_vconv_{uid}")
        post_vscale = Gst.ElementFactory.make("videoscale", f"post_vscale_{uid}")
        post_vcaps = Gst.ElementFactory.make("capsfilter", f"post_vcaps_{uid}")
        post_vcaps.set_property("caps", Gst.Caps.from_string(self.get_caps('video')))

        vf_in = Gst.ElementFactory.make("identity", f"vf_in_{uid}")
        vf_in.set_property("silent", True)
        vf_out = Gst.ElementFactory.make("identity", f"vf_out_{uid}")
        vf_out.set_property("silent", True)

        # === AUDIO CHAIN ===
        # Mirror the video compositor pattern exactly:
        # fallback → audiomixer ← real audio (through clocksync)
        # audiomixer → post-processing → audio_tee
        aqueue = Gst.ElementFactory.make("queue", f"aqueue_{uid}")
        aqueue.set_property("max-size-time", 300000000)
        volume = Gst.ElementFactory.make("volume", f"volume_{uid}")
        volume.set_property("volume", self.data.volume)
        af_in = Gst.ElementFactory.make("identity", f"af_in_{uid}")
        af_in.set_property("silent", True)
        af_out = Gst.ElementFactory.make("identity", f"af_out_{uid}")
        af_out.set_property("silent", True)
        audioconvert = Gst.ElementFactory.make("audioconvert", f"audioconvert_{uid}")
        audiorate = Gst.ElementFactory.make("audiorate", f"audiorate_{uid}")
        audiorate.set_property("skip-to-first", True)
        audioresample = Gst.ElementFactory.make("audioresample", f"audioresample_{uid}")
        acapsfilter = Gst.ElementFactory.make("capsfilter", f"acapsfilter_{uid}")
        acapsfilter.set_property("caps", Gst.Caps.from_string(self.get_caps('audio')))
        aclocksync = Gst.ElementFactory.make("clocksync", f"aclocksync_{uid}")
        aclocksync.set_property("sync-to-first", True)

        # Per-input audiomixer (FLUSH barrier for audio).
        # start_time_selection=1 (FIRST): audiomixer starts at the fallback's running_time
        # which matches the pipeline clock. With ZERO, output running_time starts at 0
        # which is hundreds of seconds late relative to the pipeline → downstream drops it.
        # Scene mixer uses FIRST for the same reason.
        _audiomixer_type = Gst.ElementFactory.find("audiomixer").get_element_type()
        input_audiomixer = GObject.new(_audiomixer_type,
            name=f"input_audiomixer_{uid}",
            force_live=True,
            latency=150000000,
            ignore_inactive_pads=True,
            start_time_selection=1)

        fallback_audiosrc = Gst.ElementFactory.make("audiotestsrc", f"fallback_audiosrc_{uid}")
        fallback_audiosrc.set_property("do-timestamp", True)
        fallback_audiosrc.set_property("is-live", True)
        fallback_audiosrc.set_property("wave", 4)
        fallback_acaps = Gst.ElementFactory.make("capsfilter", f"fallback_acaps_{uid}")
        fallback_acaps.set_property("caps", Gst.Caps.from_string(self.get_caps('audio')))

        post_acaps = Gst.ElementFactory.make("capsfilter", f"post_acaps_{uid}")
        post_acaps.set_property("caps", Gst.Caps.from_string(self.get_caps('audio')))
        level = Gst.ElementFactory.make("level", f"level_{uid}")
        level.set_property("interval", 200000000)
        level.set_property("post-messages", True)

        # === Fakesinks ===
        video_fakesink = Gst.ElementFactory.make("fakesink", f"video_fakesink_{uid}")
        video_fakesink.set_property("sync", False)
        video_fakesink.set_property("async", False)
        audio_fakesink = Gst.ElementFactory.make("fakesink", f"audio_fakesink_{uid}")
        audio_fakesink.set_property("sync", False)
        audio_fakesink.set_property("async", False)
        vqueue_sync = Gst.ElementFactory.make("queue", f"vqueue_sync_{uid}")
        vqueue_sync.set_property("leaky", 2)
        vqueue_sync.set_property("max-size-buffers", 1)
        aqueue_sync = Gst.ElementFactory.make("queue", f"aqueue_sync_{uid}")
        aqueue_sync.set_property("leaky", 2)
        aqueue_sync.set_property("max-size-buffers", 1)

        # === Add all elements ===
        for elem in [uridecodebin,
                     vqueue, videoconvert, videoscale, videorate, vcapsfilter, vclocksync,
                     input_videomixer, fallback_videosrc, fallback_vcaps,
                     post_vrate, post_vconv, post_vscale, post_vcaps, vf_in, vf_out, video_tee,
                     aqueue, volume, af_in, af_out, audioconvert, audiorate, audioresample, acapsfilter, aclocksync,
                     input_audiomixer, fallback_audiosrc, fallback_acaps,
                     post_acaps, level, audio_tee,
                     vqueue_sync, video_fakesink, aqueue_sync, audio_fakesink]:
            container.add(elem)

        # === Link video ===
        vqueue.link(videoconvert)
        videoconvert.link(videoscale)
        videoscale.link(videorate)
        videorate.link(vcapsfilter)
        vcapsfilter.link(vclocksync)
        fallback_videosrc.link(fallback_vcaps)
        fallback_vcaps.link(input_videomixer)
        vclocksync.link(input_videomixer)
        input_videomixer.link(post_vrate)
        post_vrate.link(post_vconv)
        post_vconv.link(post_vscale)
        post_vscale.link(post_vcaps)
        post_vcaps.link(vf_in)
        vf_in.link(vf_out)
        vf_out.link(video_tee)
        video_tee.link(vqueue_sync)
        vqueue_sync.link(video_fakesink)

        # === Link audio (same pattern as video) ===
        aqueue.link(audioconvert)
        audioconvert.link(volume)
        volume.link(af_in)
        af_in.link(af_out)
        af_out.link(audiorate)
        audiorate.link(audioresample)
        audioresample.link(acapsfilter)
        acapsfilter.link(aclocksync)
        # Fallback first (sink_0), then real audio (sink_1)
        fallback_audiosrc.link(fallback_acaps)
        fallback_acaps.link(input_audiomixer)
        aclocksync.link(input_audiomixer)
        input_audiomixer.link(post_acaps)
        post_acaps.link(level)
        level.link(audio_tee)
        audio_tee.link(aqueue_sync)
        aqueue_sync.link(audio_fakesink)

        # === Dynamic pad linking ===
        # Instance attributes so subclasses (PlaylistInput) can reset them
        self._video_linked = [False]
        self._audio_linked = [False]
        self._vclocksync = vclocksync
        self._aclocksync = aclocksync
        self._vqueue = vqueue
        self._aqueue = aqueue
        self._container = container

        def on_pad_added(element, pad):
            """Link pads synchronously — pad operations are thread-safe in GStreamer."""
            try:
                caps = pad.get_current_caps()
                if not caps:
                    caps = pad.query_caps(None)
                if not caps or caps.get_size() == 0:
                    return
                caps_str = caps.to_string()
                try:
                    structure = Gst.Structure.from_string(caps_str)[0]
                except (TypeError, IndexError):
                    structure = None
                name = structure.get_name() if structure else caps_str.split(",")[0]

                if name.startswith("video/") and not self._video_linked[0]:
                    self._link_video_pad(pad, structure)
                elif name.startswith("audio/") and not self._audio_linked[0]:
                    self._link_audio_pad(pad)
            except Exception as e:
                logger.log(f"Exception in on_pad_added for {uid}: {e}", level='ERROR')

        self._pad_added_signal_id = uridecodebin.connect("pad-added", on_pad_added)

        # === Store references ===
        self.uridecodebin = uridecodebin
        self.video_tee = video_tee
        self.audio_tee = audio_tee
        self.input_videomixer = input_videomixer
        self.input_audiomixer = input_audiomixer
        self.volume_element = volume
        self._fallback_videosrc = fallback_videosrc
        self._fallback_audiosrc = fallback_audiosrc

        # === Event probes (EOS + SEGMENT offset refresh) ===
        # Drop EOS at the compositor/audiomixer boundary so it doesn't
        # kill the aggregator. Playlist and loop handle EOS internally.
        # After a flush seek, refresh pad offsets on the next SEGMENT.
        _video_needs_offset = [False]
        _audio_needs_offset = [False]

        def video_event_probe(pad, info, user_data):
            try:
                event = info.get_event()
                if event.type == Gst.EventType.EOS:
                    logger.log(f"EOS at input_videomixer_{uid} real pad", level='DEBUG')
                    if not self.handle_eos():
                        self.data.state = "EOS"
                        safe_broadcast("UPDATE", self.data)
                    return Gst.PadProbeReturn.DROP
                elif event.type in (Gst.EventType.STREAM_START, Gst.EventType.FLUSH_START):
                    _video_needs_offset[0] = True
                    logger.log(f"[{uid}] video probe: {event.type.value_nick} → needs_offset=True", level='DEBUG')
                elif event.type == Gst.EventType.SEGMENT and _video_needs_offset[0]:
                    _video_needs_offset[0] = False
                    logger.log(f"[{uid}] video probe: SEGMENT → refreshing offset", level='DEBUG')
                    if not self._is_live:
                        self._refresh_pad_offset(pad, "video")
                return Gst.PadProbeReturn.OK
            except Exception as e:
                logger.log(f"Exception in video_event_probe: {e}", level='ERROR')
                return Gst.PadProbeReturn.OK

        def audio_event_probe(pad, info, user_data):
            try:
                event = info.get_event()
                if event.type == Gst.EventType.EOS:
                    logger.log(f"EOS at input_audiomixer_{uid} real pad", level='DEBUG')
                    if not self.handle_eos():
                        self.data.state = "EOS"
                        safe_broadcast("UPDATE", self.data)
                    return Gst.PadProbeReturn.DROP
                elif event.type in (Gst.EventType.STREAM_START, Gst.EventType.FLUSH_START):
                    _audio_needs_offset[0] = True
                    logger.log(f"[{uid}] audio probe: {event.type.value_nick} → needs_offset=True", level='DEBUG')
                elif event.type == Gst.EventType.SEGMENT and _audio_needs_offset[0]:
                    _audio_needs_offset[0] = False
                    logger.log(f"[{uid}] audio probe: SEGMENT → refreshing offset", level='DEBUG')
                    if not self._is_live:
                        self._refresh_pad_offset(pad, "audio")
                return Gst.PadProbeReturn.OK
            except Exception as e:
                logger.log(f"Exception in audio_event_probe: {e}", level='ERROR')
                return Gst.PadProbeReturn.OK

        video_real_pad = vclocksync.get_static_pad("src").get_peer()
        if video_real_pad:
            self._video_event_probe_id = video_real_pad.add_probe(
                Gst.PadProbeType.EVENT_DOWNSTREAM | Gst.PadProbeType.EVENT_FLUSH,
                video_event_probe, None)
            self._video_event_probe_pad = video_real_pad

        audio_real_pad = aclocksync.get_static_pad("src").get_peer()
        if audio_real_pad:
            self._audio_event_probe_id = audio_real_pad.add_probe(
                Gst.PadProbeType.EVENT_DOWNSTREAM | Gst.PadProbeType.EVENT_FLUSH,
                audio_event_probe, None)
            self._audio_event_probe_pad = audio_real_pad

        logger.log(f"uridecodebin3 bin created for {uid}: uri={uri}", level='DEBUG')
        return container

    def _link_video_pad(self, pad, structure):
        """Link video pad from uridecodebin3. Runs on GLib thread."""
        if self._video_linked[0]:
            return False
        uid = self.data.uid
        sink_pad = self._vqueue.get_static_pad("sink")
        if sink_pad.is_linked():
            logger.log(f"uridecodebin3 {uid} video pad: sink already linked, skipping", level='DEBUG')
            return False
        try:
            pad.link(sink_pad)
            self._video_linked[0] = True
            self.data.has_video = ConfigReader().get_enable_video()
            logger.log(f"uridecodebin3 {uid} video pad linked", level='DEBUG')
            self._on_video_pad_linked()
            if structure:
                w = structure.get_int('width')
                h = structure.get_int('height')
                if w[0]:
                    self.data.width = w[1]
                if h[0]:
                    self.data.height = h[1]
            success, duration = pad.query_duration(Gst.Format.TIME)
            if success and duration > 0:
                self.data.duration = duration // Gst.SECOND
            safe_broadcast("UPDATE", self.data)
            GLib.idle_add(self._relink_to_mixers)

            # Set initial pad offset to align timestamps with pipeline clock.
            # This is approximate (stale by decode startup time) but sufficient for clip 1.
            # The event probe refreshes this to an exact value when SEGMENT arrives.
            real_video_pad = self._vclocksync.get_static_pad("src").get_peer()
            if real_video_pad and not self._is_live:
                container = self._container
                pipeline = container.get_parent() if container else None
                if pipeline:
                    clock = pipeline.get_clock()
                    if clock:
                        now = clock.get_time()
                        base_time = pipeline.get_base_time()
                        pipeline_rt = now - base_time
                        real_video_pad.set_offset(pipeline_rt)
                        self._real_video_pad = real_video_pad
                        logger.log(f"[OFFSET] Video pad offset set to {pipeline_rt // Gst.MSECOND}ms (link-time)", level='DEBUG')
            elif real_video_pad:
                self._real_video_pad = real_video_pad
        except Exception as e:
            logger.log(f"uridecodebin3 {uid} video link failed: {e}", level='ERROR')
        return False

    def _link_audio_pad(self, pad):
        """Link audio pad from uridecodebin3. Runs on GLib thread."""
        if self._audio_linked[0]:
            return False
        uid = self.data.uid
        sink_pad = self._aqueue.get_static_pad("sink")
        if sink_pad.is_linked():
            logger.log(f"uridecodebin3 {uid} audio pad: sink already linked, skipping", level='DEBUG')
            return False
        try:
            pad.link(sink_pad)
            self._audio_linked[0] = True
            self.data.has_audio = ConfigReader().get_enable_audio()
            logger.log(f"uridecodebin3 {uid} audio pad linked", level='DEBUG')

            # Set initial pad offset (same as video — see _link_video_pad).
            real_audio_pad = self._aclocksync.get_static_pad("src").get_peer()
            if real_audio_pad and not self._is_live:
                container = self._container
                pipeline = container.get_parent() if container else None
                if pipeline:
                    clock = pipeline.get_clock()
                    if clock:
                        now = clock.get_time()
                        base_time = pipeline.get_base_time()
                        pipeline_rt = now - base_time
                        real_audio_pad.set_offset(pipeline_rt)
                        self._real_audio_pad = real_audio_pad
                        logger.log(f"[OFFSET] Audio pad offset set to {pipeline_rt // Gst.MSECOND}ms (link-time)", level='DEBUG')
            elif real_audio_pad:
                self._real_audio_pad = real_audio_pad
            safe_broadcast("UPDATE", self.data)
            GLib.idle_add(self._relink_to_mixers)
        except Exception as e:
            logger.log(f"uridecodebin3 {uid} audio link failed: {e}", level='ERROR')
        return False

    def handle_eos(self) -> bool:
        """Handle EOS for looping. Returns True if handled (don't propagate)."""
        if self.data.loop and self.uridecodebin:
            if getattr(self, '_looping', False):
                return True
            self._looping = True
            logger.log(f"uridecodebin3 {self.data.uid} looping via flush seek", level='DEBUG')
            GLib.idle_add(self._do_loop_seek)
            return True
        if getattr(self, '_stopping', False):
            return False
        self._stopping = True
        if self.uridecodebin:
            GLib.idle_add(self._stop_source)
        return False

    def _stop_source(self):
        """Stop entire input bin after EOS."""
        uid = self.data.uid
        container = getattr(self, '_bin', None)
        if container:
            container.set_locked_state(True)
            container.set_state(Gst.State.NULL)
        self.uridecodebin = None
        self._fallback_videosrc = None
        logger.log(f"uridecodebin3 {uid} bin stopped (EOS, no loop)", level='DEBUG')
        return False

    def _do_loop_seek(self):
        """Execute loop seek from GLib main loop context."""
        if self.uridecodebin:
            # Pad offsets are refreshed in FLUSH_STOP probes (not here).
            # Setting offsets before seek is too early — by the time new data
            # arrives after the flush, the audiomixer has advanced past the
            # pre-seek offset, causing audio to be dropped as "too late."
            seek_event = Gst.Event.new_seek(
                1.0, Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                Gst.SeekType.SET, 0,
                Gst.SeekType.NONE, 0
            )
            self.uridecodebin.send_event(seek_event)
        self._looping = False
        return False

    def _refresh_pad_offset(self, pad, stream_type):
        """Update pad offset to current pipeline running_time.

        Called from event probes on SEGMENT (after STREAM_START or FLUSH_START).
        This is right before data arrives, so the offset matches the aggregator's
        current position — unlike link-time offset which goes stale during decode startup.
        """
        try:
            container = getattr(self, '_bin', None) or getattr(self, '_container', None)
            if not container:
                return
            pipeline = container.get_parent()
            if not pipeline:
                return
            clock = pipeline.get_clock()
            if not clock:
                return
            now = clock.get_time()
            base_time = pipeline.get_base_time()
            pipeline_rt = now - base_time
            pad.set_offset(pipeline_rt)
            logger.log(f"[OFFSET] {stream_type} pad offset set to {pipeline_rt // Gst.MSECOND}ms (SEGMENT refresh)", level='DEBUG')
        except Exception as e:
            logger.log(f"Exception in _refresh_pad_offset: {e}", level='ERROR')

    def _update_pad_offsets(self):
        """Recompute pad offsets to match current pipeline running_time."""
        container = getattr(self, '_bin', None)
        if not container:
            return
        pipeline = container.get_parent()
        if not pipeline:
            return
        clock = pipeline.get_clock()
        if not clock:
            return
        now = clock.get_time()
        base_time = pipeline.get_base_time()
        pipeline_rt = now - base_time

        for pad_name, pad in [("video", getattr(self, '_real_video_pad', None)),
                              ("audio", getattr(self, '_real_audio_pad', None))]:
            if pad:
                pad.set_offset(pipeline_rt)
                logger.log(f"Loop: {pad_name} pad offset updated to {pipeline_rt // Gst.MSECOND}ms", level='DEBUG')

    def _relink_to_mixers(self):
        """Re-trigger link_source on all mixers that have this input assigned."""
        try:
            from pipeline_handler import HandlerSingleton
            handler = HandlerSingleton()
            mixers = handler.get_pipelines('mixers')
            if not mixers:
                return False
            for mixer in mixers:
                if not hasattr(mixer, 'data') or not hasattr(mixer.data, 'sources'):
                    continue
                for source in mixer.data.sources:
                    if source.src == str(self.data.uid):
                        # Fast-path skip if slot already has matching queues — saves a scheduling round-trip
                        slot_queues = getattr(mixer, '_slot_queues', {}).get(source.index, {})
                        have_video_q = "video" in slot_queues
                        have_audio_q = "audio" in slot_queues
                        expected_video = getattr(self.data, 'has_video', True)
                        expected_audio = getattr(self.data, 'has_audio', True)
                        if have_video_q == expected_video and have_audio_q == expected_audio:
                            continue
                        mixer.link_source(source.index, self.data.uid)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Failed to relink to mixers: %s", e)
        return False

    def _on_video_pad_linked(self):
        """Called when uridecodebin3 video pad links. Override in subclasses."""
        pass

    def handle_error(self, err_message):
        """Called by core_pipeline._on_error on bus error."""
        logger.log(f"Uridecodebin3 {self.data.uid} error: {err_message}", level='ERROR')
        self.data.state = "ERROR"
        self.data.details = err_message
        safe_broadcast("UPDATE", self.data)

    def get_pipeline(self):
        """Return queryable element for position/duration/seeking."""
        return self.uridecodebin
