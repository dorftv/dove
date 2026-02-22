"""
WHIP ingest input — receives WebRTC screen share / camera via WHIP protocol.

Creates a fallback testsrc (black video + silence) until a publisher connects.
When a WHIP offer arrives, a separate Gst.Pipeline with webrtcbin (receive mode)
is created, connected to the input bin via proxysink/proxysrc.

SDP negotiation runs entirely on the GLib thread (no worker threads):
- set-remote-description / set-local-description: fire-and-forget (promise.interrupt())
- create-answer: Gst.Promise.new_with_change_func(callback)
- IMPORTANT: GObject wrapper for answer evaluates as falsy — use `is None` check
- ICE gathering polled via GLib.timeout_add
"""

from api.inputs.whip import WhipInputDTO
from .input import Input
from gi.repository import Gst, GLib

import gi
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import GstWebRTC, GstSdp

from api.webrtc_utils import (
    get_pipeline, configure_webrtcbin,
    inject_ice_candidates, rewrite_sdp_candidates,
    patch_offer_h264_profile,
)
from event_loop_bridge import safe_broadcast
from logger import logger

# Prevent libnice GC segfault — same pattern as WHEP (see CLAUDE.md "webrtcbin Cleanup")
_orphaned_webrtcbins: list = []

# ICE gathering poll: 10ms interval, max 200 attempts = 2s timeout
ICE_POLL_INTERVAL_MS = 10
ICE_POLL_MAX_ATTEMPTS = 200

# Codec → depayloader element name
VIDEO_DEPAY_ELEMENTS = {
    'H264': 'rtph264depay',
    'VP8': 'rtpvp8depay',
    'VP9': 'rtpvp9depay',
    'AV1': 'rtpav1depay',
}

# Codec → decoder candidates (HW-accelerated first, software fallback)
VIDEO_DECODER_CANDIDATES = {
    'H264': ['vah264dec', 'avdec_h264', 'openh264dec'],
    'VP8': ['vp8dec'],
    'VP9': ['vavp9dec', 'vp9dec'],
    'AV1': ['vaav1dec', 'av1dec'],
}


class WhipInput(Input):
    data: WhipInputDTO

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._publisher_pipeline = None
        self._publisher_webrtcbin = None
        self._ice_agent_ref = None
        self._ice_candidates = []
        self._signal_ids = []
        self._video_proxy_src = None
        self._video_proxy_sink = None
        self._publisher_connected = False
        self._publisher_claimed = False
        self._fallback_video_downstream_pad = None  # pad that was linked to testsrc
        # Suppress transient not-linked errors from videotestsrc during filter rebuilds/swaps
        self._suppress_teardown_error = True

    @property
    def is_publishing(self) -> bool:
        return self._publisher_connected

    def try_claim(self) -> bool:
        """Atomic check-and-set for publisher session ownership. Safe because it contains no await."""
        if self._publisher_pipeline is not None or self._publisher_claimed:
            return False
        self._publisher_claimed = True
        return True

    def build_pipeline_str(self) -> str:
        """Fallback: black video until publisher connects. Video-only input."""
        uid = self.data.uid
        self.data.has_audio = False
        return (
            f" videotestsrc do-timestamp=true is-live=true pattern=2 "
            f" name=videotestsrc_{uid} ! {self.get_caps('video')} ! {self.get_video_end()} "
        )

    # ── SDP negotiation ──────────────────────────────────────────────

    def connect_publisher(self, sdp_offer: str, answer_future, loop, host_ip: str = None):
        """Set up webrtcbin to receive WebRTC stream. Runs entirely on GLib thread."""

        def do_setup_and_negotiate():
            try:
                uid = self.data.uid
                uid_short = str(uid)[:8]
                main_pipeline = get_pipeline()

                # Separate publisher pipeline (like WHEP viewer pipelines)
                publisher_pipeline = Gst.Pipeline.new(f"whip_pub_{uid_short}")
                publisher_pipeline.use_clock(main_pipeline.get_clock())
                publisher_pipeline.set_base_time(main_pipeline.get_base_time())
                publisher_pipeline.set_start_time(Gst.CLOCK_TIME_NONE)

                webrtcbin = Gst.ElementFactory.make("webrtcbin", f"whip_wb_{uid_short}")
                if not webrtcbin:
                    logger.log("WHIP: webrtcbin element not available", level='ERROR')
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return False

                self._ice_agent_ref = configure_webrtcbin(webrtcbin)
                publisher_pipeline.add(webrtcbin)

                self._publisher_pipeline = publisher_pipeline
                self._publisher_webrtcbin = webrtcbin
                self._ice_candidates = []

                self._signal_ids = [
                    webrtcbin.connect('on-ice-candidate', self._on_ice_candidate),
                    webrtcbin.connect('notify::ice-connection-state', self._on_ice_state),
                    webrtcbin.connect('pad-added', self._on_pad_added),
                ]

                publisher_pipeline.set_state(Gst.State.PLAYING)

                # ── SDP negotiation (all on GLib thread, no promise.wait) ──
                patched_offer = patch_offer_h264_profile(sdp_offer)
                res, sdp_message = GstSdp.SDPMessage.new_from_text(patched_offer)
                if res != GstSdp.SDPResult.OK:
                    logger.log("WHIP: failed to parse SDP offer", level='ERROR')
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return False

                offer_description = GstWebRTC.WebRTCSessionDescription.new(
                    GstWebRTC.WebRTCSDPType.OFFER, sdp_message)

                # Step 1: set remote description (fire-and-forget)
                set_remote_promise = Gst.Promise.new()
                webrtcbin.emit('set-remote-description', offer_description, set_remote_promise)
                set_remote_promise.interrupt()

                # Step 2: create answer (callback fires when ready)
                def on_answer_created(answer_promise):
                    try:
                        reply = answer_promise.get_reply()
                        answer_description = reply.get_value('answer') if reply else None
                        # GObject wrapper evaluates as falsy — must use `is None`
                        if answer_description is None:
                            logger.log("WHIP: no answer in reply", level='ERROR')
                            loop.call_soon_threadsafe(answer_future.set_result, None)
                            return

                        # Step 3: set local description (fire-and-forget)
                        set_local_promise = Gst.Promise.new()
                        webrtcbin.emit('set-local-description', answer_description, set_local_promise)
                        set_local_promise.interrupt()

                        # Step 4: poll ICE gathering until complete
                        poll_count = [0]

                        def poll_ice_gathering():
                            poll_count[0] += 1
                            gathering_state = webrtcbin.get_property('ice-gathering-state')
                            if gathering_state == GstWebRTC.WebRTCICEGatheringState.COMPLETE or poll_count[0] >= ICE_POLL_MAX_ATTEMPTS:
                                self._resolve_sdp_answer(webrtcbin, host_ip, loop, answer_future, uid_short)
                                return False  # stop polling
                            return True  # continue

                        GLib.timeout_add(ICE_POLL_INTERVAL_MS, poll_ice_gathering)

                    except Exception as e:
                        logger.log(f"WHIP on_answer_created error: {e}", level='ERROR')
                        loop.call_soon_threadsafe(answer_future.set_result, None)

                create_answer_promise = Gst.Promise.new_with_change_func(on_answer_created)
                webrtcbin.emit('create-answer', None, create_answer_promise)

            except Exception as e:
                import traceback
                logger.log(f"WHIP setup error: {e}\n{traceback.format_exc()}", level='ERROR')
                loop.call_soon_threadsafe(answer_future.set_result, None)
            return False

        GLib.idle_add(do_setup_and_negotiate)

    def _resolve_sdp_answer(self, webrtcbin, host_ip, loop, answer_future, uid_short):
        """Collect ICE candidates and resolve the asyncio future with SDP answer text."""
        local_description = webrtcbin.get_property('local-description')
        if local_description is None:
            loop.call_soon_threadsafe(answer_future.set_result, None)
            return

        sdp_text = local_description.sdp.as_text()
        candidates = list(self._ice_candidates)
        self._ice_candidates = []
        sdp_text = inject_ice_candidates(sdp_text, candidates)
        if host_ip:
            sdp_text = rewrite_sdp_candidates(sdp_text, host_ip)

        logger.log(f"WHIP: answer ready for {uid_short} ({len(candidates)} candidates)", level='INFO')
        loop.call_soon_threadsafe(answer_future.set_result, sdp_text)

    # ── Incoming media handling ──────────────────────────────────────

    def _on_pad_added(self, webrtcbin, pad):
        """Handle new src pads from webrtcbin — decode video and bridge to input bin."""
        caps = pad.get_current_caps() or pad.query_caps(None)
        if not caps or caps.get_size() == 0:
            return

        struct = caps.get_structure(0)
        if struct.get_name() != "application/x-rtp":
            return

        media_type = struct.get_string("media") or ""
        encoding = struct.get_string("encoding-name") or ""
        uid_short = str(self.data.uid)[:8]
        logger.log(f"WHIP pad-added: media={media_type} encoding={encoding} for {uid_short}", level='INFO')

        if media_type == "video":
            self._handle_video_pad(pad, encoding, uid_short)
        elif media_type == "audio":
            # Screen sharing is video-only. Audio pads are ignored.
            # TODO: add audio support for camera input (getUserMedia with audio)
            logger.log(f"WHIP: ignoring audio pad ({encoding})", level='DEBUG')

    def _handle_video_pad(self, pad, encoding, uid_short):
        """Build decode chain in publisher pipeline and bridge to input bin via proxysink/proxysrc."""
        publisher_pipeline = self._publisher_pipeline

        depay_element_name = VIDEO_DEPAY_ELEMENTS.get(encoding)
        if not depay_element_name:
            logger.log(f"WHIP: unsupported video codec {encoding}", level='WARNING')
            return

        # Find best available decoder (HW-accelerated preferred)
        decoder_element_name = None
        for candidate in VIDEO_DECODER_CANDIDATES.get(encoding, []):
            if Gst.ElementFactory.find(candidate):
                decoder_element_name = candidate
                break
        if not decoder_element_name:
            logger.log(f"WHIP: no decoder available for {encoding}", level='ERROR')
            return

        # Build: depay → decoder → videoconvert → videoscale → capsfilter → proxysink
        depayloader = Gst.ElementFactory.make(depay_element_name, f"whip_vdepay_{uid_short}")
        decoder = Gst.ElementFactory.make(decoder_element_name, f"whip_vdec_{uid_short}")
        video_convert = Gst.ElementFactory.make("videoconvert", f"whip_vconv_{uid_short}")
        video_scale = Gst.ElementFactory.make("videoscale", f"whip_vscale_{uid_short}")
        video_caps = Gst.ElementFactory.make("capsfilter", f"whip_vcaps_{uid_short}")
        video_caps.set_property("caps", Gst.Caps.from_string(self.get_caps('video')))
        video_proxy_sink = Gst.ElementFactory.make("proxysink", f"whip_vpsink_{uid_short}")

        for element in (depayloader, decoder, video_convert, video_scale, video_caps, video_proxy_sink):
            publisher_pipeline.add(element)
            element.sync_state_with_parent()

        pad.link(depayloader.get_static_pad("sink"))
        depayloader.link(decoder)
        decoder.link(video_convert)
        video_convert.link(video_scale)
        video_scale.link(video_caps)
        video_caps.link(video_proxy_sink)

        self._video_proxy_sink = video_proxy_sink
        logger.log(f"WHIP: video chain: {depay_element_name} → {decoder_element_name} → proxysink", level='INFO')

        # Defer proxysrc wiring to next GLib iteration (avoid re-entrancy in pad-added)
        def wire_video_proxy_src():
            video_proxy_src = Gst.ElementFactory.make("proxysrc", f"whip_vpsrc_{uid_short}")
            video_proxy_src.set_property("proxysink", video_proxy_sink)
            self._video_proxy_src = video_proxy_src
            self._swap_fallback_for_proxy(video_proxy_src)
            return False

        GLib.idle_add(wire_video_proxy_src)

    def _swap_fallback_for_proxy(self, video_proxy_src):
        """Replace fallback videotestsrc with proxysrc in the input bin.

        Unlinks the testsrc src pad from its downstream peer (first capsfilter),
        then links the proxysrc to that same peer. The full processing chain
        (videorate → videoconvert → videoscale → capsfilter → tee) stays intact.
        """
        uid = self.data.uid
        input_bin = self._bin
        if not input_bin:
            logger.log(f"WHIP: no input bin for {uid}", level='ERROR')
            return

        fallback_src_name = f"videotestsrc_{uid}"
        fallback_element = input_bin.get_by_name(fallback_src_name)
        if not fallback_element:
            logger.log(f"WHIP: fallback {fallback_src_name} not found", level='ERROR')
            return

        fallback_src_pad = fallback_element.get_static_pad("src")
        downstream_sink_pad = fallback_src_pad.get_peer()
        if not downstream_sink_pad:
            logger.log(f"WHIP: {fallback_src_name} has no downstream peer", level='ERROR')
            return

        # Save for reconnection on publisher disconnect
        self._fallback_video_downstream_pad = downstream_sink_pad

        # Stop testsrc FIRST so it doesn't push into unlinked pad
        fallback_element.set_state(Gst.State.NULL)

        # Swap: unlink stopped testsrc, link proxysrc to same downstream element
        fallback_src_pad.unlink(downstream_sink_pad)

        input_bin.add(video_proxy_src)
        video_proxy_src.sync_state_with_parent()

        link_result = video_proxy_src.get_static_pad("src").link(downstream_sink_pad)
        if link_result != Gst.PadLinkReturn.OK:
            logger.log(f"WHIP: proxysrc link failed: {link_result}", level='ERROR')
            fallback_element.set_state(Gst.State.PLAYING)
            fallback_src_pad.link(downstream_sink_pad)
            return

        self._publisher_connected = True
        self.data.state = "PLAYING"
        safe_broadcast("UPDATE", self.data)
        logger.log(f"WHIP: video swap complete for {uid}", level='INFO')

    # ── ICE signal handlers ──────────────────────────────────────────

    def _on_ice_candidate(self, webrtcbin, sdp_mline_index, candidate):
        self._ice_candidates.append({
            'sdpMLineIndex': sdp_mline_index,
            'candidate': candidate,
        })

    def _on_ice_state(self, webrtcbin, pspec):
        try:
            state = webrtcbin.get_property("ice-connection-state")
            state_name = state.value_nick if hasattr(state, 'value_nick') else str(state)
            logger.log(f"WHIP ICE: {state_name}", level='INFO')
            if state in (GstWebRTC.WebRTCICEConnectionState.FAILED,
                         GstWebRTC.WebRTCICEConnectionState.CLOSED):
                GLib.idle_add(self._handle_publisher_disconnect)
        except Exception as e:
            logger.log(f"WHIP ICE state error: {e}", level='ERROR')

    def _handle_publisher_disconnect(self):
        """Called when ICE connection fails/closes. Cleans up and restores fallback."""
        self.disconnect_publisher()
        return False

    def add_ice_candidate(self, sdp_mline_index: int, candidate: str):
        """Add trickle ICE candidate (called from GLib thread)."""
        if self._publisher_webrtcbin:
            self._publisher_webrtcbin.emit('add-ice-candidate', sdp_mline_index, candidate)

    # ── Disconnect & cleanup ─────────────────────────────────────────

    def disconnect_publisher(self):
        """Tear down publisher pipeline. Orphans webrtcbin (libnice crash workaround)."""
        webrtcbin = self._publisher_webrtcbin
        publisher_pipeline = self._publisher_pipeline

        # Always release the claim, even on early-return paths where
        # connect_publisher failed before assigning _publisher_pipeline.
        # Otherwise a failed POST would leave the input permanently 409-locked.
        self._publisher_claimed = False

        if not publisher_pipeline:
            return

        # Disconnect signal handlers
        if webrtcbin:
            for signal_id in self._signal_ids:
                try:
                    webrtcbin.handler_disconnect(signal_id)
                except Exception as e:
                    logger.log(f"WHIP: signal disconnect failed: {e}", level='DEBUG')
        self._signal_ids = []
        self._ice_agent_ref = None

        # Remove proxysrc from input bin
        if self._video_proxy_src:
            src_pad = self._video_proxy_src.get_static_pad("src")
            if src_pad:
                peer = src_pad.get_peer()
                if peer:
                    src_pad.unlink(peer)
            self._video_proxy_src.set_state(Gst.State.NULL)
            parent = self._video_proxy_src.get_parent()
            if parent:
                parent.remove(self._video_proxy_src)

        self._video_proxy_src = None
        self._video_proxy_sink = None

        # Safe webrtcbin disposal: READY → flush bus → remove → NULL → orphan
        publisher_pipeline.set_state(Gst.State.READY)
        if webrtcbin:
            bus = publisher_pipeline.get_bus()
            if bus:
                bus.set_flushing(True)
            publisher_pipeline.remove(webrtcbin)
        publisher_pipeline.set_state(Gst.State.NULL)

        if webrtcbin:
            _orphaned_webrtcbins.append(webrtcbin)
            logger.log(f"WHIP: disposed publisher (orphaned webrtcbins: {len(_orphaned_webrtcbins)})", level='WARNING')

        self._publisher_pipeline = None
        self._publisher_webrtcbin = None
        self._publisher_connected = False

        # Restore fallback videotestsrc
        self._restore_video_fallback()

        self.data.state = "NEW"
        self.data.details = None
        safe_broadcast("UPDATE", self.data)

    def _restore_video_fallback(self):
        """Reconnect fallback videotestsrc after publisher disconnects."""
        uid = self.data.uid
        input_bin = self._bin
        saved_downstream_pad = self._fallback_video_downstream_pad
        self._fallback_video_downstream_pad = None

        if not input_bin or not saved_downstream_pad:
            return

        fallback_element = input_bin.get_by_name(f"videotestsrc_{uid}")
        if not fallback_element:
            return

        # Relink testsrc src pad to its original downstream peer
        fallback_src_pad = fallback_element.get_static_pad("src")
        link_result = fallback_src_pad.link(saved_downstream_pad)
        if link_result == Gst.PadLinkReturn.OK:
            fallback_element.set_state(Gst.State.PLAYING)
            logger.log(f"WHIP: restored video fallback for {uid}", level='INFO')
        else:
            logger.log(f"WHIP: failed to restore video fallback: {link_result}", level='WARNING')

    def cleanup(self):
        """Called when input is deleted."""
        if self._publisher_pipeline:
            self.disconnect_publisher()
        try:
            from api.webrtc_whip import remove_resources_for_input
            remove_resources_for_input(str(self.data.uid))
        except Exception as e:
            logger.log(
                f"WHIP cleanup: remove_resources_for_input failed: {e}",
                level='WARNING',
            )
        self._fallback_video_downstream_pad = None
