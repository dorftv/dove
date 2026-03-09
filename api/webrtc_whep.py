"""
Native WHEP server for WebRTC previews.

Always-on preview encoder entities per source + per-viewer webrtcbin with RTP payloaders.
Encoder entities created by pipeline_handler when input/mixer is added.

Architecture: each viewer gets a separate Gst.Pipeline connected to the main pipeline
via proxysink/proxysrc (zero-copy, caps-agnostic). On disconnect: READY (cleans ICE),
release request pads, flush bus, remove webrtcbin, NULL pipeline. Only the bare
webrtcbin element (~52KB) is kept alive to prevent GC finalize segfault in libnice.
"""

import asyncio
import re
import uuid
from fastapi import APIRouter, Request, Response, HTTPException

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstWebRTC', '1.0')
gi.require_version('GstSdp', '1.0')
from gi.repository import Gst, GLib, GstVideo, GstWebRTC, GstSdp

from api.webrtc_utils import (
    get_host_ip, rewrite_sdp_candidates,
    patch_offer_h264_profile, inject_ice_candidates, get_pipeline,
    configure_webrtcbin,
)
from api.auth import get_current_user_optional, is_auth_enabled
from config_handler import ConfigReader
from event_loop_bridge import bridge
from logger import logger

router = APIRouter()
config = ConfigReader()

_managers: dict[str, "WebrtcPreviewManager"] = {}  # source_uid -> manager
_resources: dict[str, tuple[str, str]] = {}  # resource_id -> (source_uid, peer_id)
# GC finalize on webrtcbin that had real ICE sessions segfaults in libnice.
# Keep refs alive (~52KB each). Pipeline and all other resources are fully freed.
_orphaned_webrtcbins: list = []


def _drop_latency_event(pad, info):
    """Prevent main-pipeline latency from inflating WHEP preview delay."""
    event = info.get_event()
    if event.type == Gst.EventType.LATENCY:
        return Gst.PadProbeReturn.DROP
    return Gst.PadProbeReturn.OK


def _extract_offer_pts(sdp_text: str) -> tuple[int | None, int | None]:
    """Extract H264 (packetization-mode=1) and Opus PTs from browser offer."""
    h264_pts = set()
    opus_pt = None
    for line in sdp_text.splitlines():
        m = re.match(r'a=rtpmap:(\d+)\s+H264/90000', line.strip())
        if m:
            h264_pts.add(int(m.group(1)))
        m = re.match(r'a=rtpmap:(\d+)\s+opus/48000', line.strip(), re.IGNORECASE)
        if m and opus_pt is None:
            opus_pt = int(m.group(1))

    video_pt = None
    for line in sdp_text.splitlines():
        m = re.match(r'a=fmtp:(\d+)\s+(.*)', line.strip())
        if m and int(m.group(1)) in h264_pts and 'packetization-mode=1' in m.group(2):
            video_pt = int(m.group(1))
            break
    return video_pt, opus_pt




class WebrtcPreviewManager:
    """Manages per-viewer webrtcbin for one source. Encoder entities are always-on.

    Each viewer gets a separate Gst.Pipeline connected via proxysink/proxysrc:
      main: enc_tee → proxysink   (in main pipeline)
      viewer: proxysrc → queue → rtppay → webrtcbin   (separate pipeline)
    """

    def __init__(self, source_uid: str):
        self.source_uid = source_uid
        self.peers: dict[str, dict] = {}

    def _find_preview_encoders(self):
        """Find existing always-on preview encoder entities for this source.

        For audio, specifically find the opus encoder (WebRTC needs opus,
        not AAC which is used by HLS).
        """
        from pipeline_handler import HandlerSingleton
        handler = HandlerSingleton()
        video_enc = None
        audio_enc = None
        for enc in handler.get_pipelines("encoders") or []:
            if str(enc.data.src) == self.source_uid and enc.data.is_preview:
                if enc.data.type == "video":
                    video_enc = enc
                elif enc.data.type == "audio" and enc.data.element == "opusenc":
                    audio_enc = enc
        return video_enc, audio_enc

    def setup_peer(self, peer_id: str, sdp_offer: str, answer_future, loop, host_ip: str = None):
        """Create per-viewer elements + negotiate SDP, all on the GLib thread."""
        def create_elements(attempt=0):
            try:
                logger.log(f"WHEP create_elements attempt={attempt} for {self.source_uid[:8]}", level='DEBUG')
                video_enc, audio_enc = self._find_preview_encoders()
                if not video_enc:
                    if attempt < 10:
                        GLib.timeout_add(200, lambda a=attempt+1: create_elements(a) or False)
                        return False
                    logger.log(f"WHEP: no preview encoders for {self.source_uid}", level='ERROR')
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return False

                video_tee = video_enc.tee
                audio_tee = audio_enc.tee if audio_enc else None
                if not video_tee:
                    logger.log(f"WHEP: video encoder tee not available", level='ERROR')
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return False

                has_audio = audio_enc is not None and audio_tee is not None
                pipeline = get_pipeline()
                pid = peer_id[:8]

                # --- Create proxysinks in main pipeline ---
                v_psink = Gst.ElementFactory.make("proxysink", f"psink_v_{pid}")
                pipeline.add(v_psink)
                v_psink.get_static_pad("sink").add_probe(
                    Gst.PadProbeType.EVENT_DOWNSTREAM, _drop_latency_event)
                v_psink.sync_state_with_parent()
                video_tee_pad = video_tee.request_pad_simple("src_%u")
                video_tee_pad.link(v_psink.get_static_pad("sink"))

                a_psink = None
                audio_tee_pad = None
                if has_audio:
                    a_psink = Gst.ElementFactory.make("proxysink", f"psink_a_{pid}")
                    pipeline.add(a_psink)
                    a_psink.get_static_pad("sink").add_probe(
                        Gst.PadProbeType.EVENT_DOWNSTREAM, _drop_latency_event)
                    a_psink.sync_state_with_parent()
                    audio_tee_pad = audio_tee.request_pad_simple("src_%u")
                    audio_tee_pad.link(a_psink.get_static_pad("sink"))

                # --- Create viewer pipeline ---
                viewer_pipe = Gst.Pipeline.new(f"viewer_{pid}")
                viewer_pipe.use_clock(pipeline.get_clock())
                viewer_pipe.set_base_time(pipeline.get_base_time())
                viewer_pipe.set_start_time(Gst.CLOCK_TIME_NONE)

                # --- Create proxysrc + payloader elements ---
                v_psrc = Gst.ElementFactory.make("proxysrc", f"psrc_v_{pid}")
                v_psrc.set_property("proxysink", v_psink)

                webrtcbin = Gst.ElementFactory.make("webrtcbin", f"wb_{pid}")
                if not webrtcbin:
                    logger.log("WHEP: webrtcbin element not available", level='ERROR')
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return False

                ice_agent_ref = configure_webrtcbin(webrtcbin)
                webrtcbin.set_property("latency", 50)

                video_pt, audio_pt = _extract_offer_pts(sdp_offer)

                vq = Gst.ElementFactory.make("queue", f"pvq_{pid}")
                vq.set_property("leaky", 2)
                vq.set_property("max-size-buffers", 1)
                vpay = Gst.ElementFactory.make("rtph264pay", f"vpay_{pid}")
                vpay.set_property("config-interval", -1)
                vpay.set_property("aggregate-mode", 1)
                if video_pt:
                    vpay.set_property("pt", video_pt)

                # --- Build viewer pipeline ---
                viewer_elements = [v_psrc, vq, vpay, webrtcbin]

                a_psrc = None
                aq = None
                apay = None
                wb_audio_sink = None
                if has_audio:
                    a_psrc = Gst.ElementFactory.make("proxysrc", f"psrc_a_{pid}")
                    a_psrc.set_property("proxysink", a_psink)
                    aq = Gst.ElementFactory.make("queue", f"paq_{pid}")
                    aq.set_property("leaky", 2)
                    aq.set_property("max-size-buffers", 1)
                    apay = Gst.ElementFactory.make("rtpopuspay", f"apay_{pid}")
                    if audio_pt:
                        apay.set_property("pt", audio_pt)
                    viewer_elements.extend([a_psrc, aq, apay])

                for e in viewer_elements:
                    viewer_pipe.add(e)

                # --- Link video chain ---
                v_psrc.link(vq)
                vq.link(vpay)
                wb_video_sink = webrtcbin.request_pad_simple("sink_%u")
                vpay.get_static_pad("src").link(wb_video_sink)

                # --- Link audio chain (optional) ---
                if has_audio:
                    a_psrc.link(aq)
                    aq.link(apay)
                    wb_audio_sink = webrtcbin.request_pad_simple("sink_%u")
                    apay.get_static_pad("src").link(wb_audio_sink)

                # --- Start viewer pipeline ---
                viewer_pipe.set_state(Gst.State.PLAYING)

                # Early keyframe request
                key_event = GstVideo.video_event_new_upstream_force_key_unit(
                    Gst.CLOCK_TIME_NONE, True, 0)
                vpay.send_event(key_event)

                # --- Store peer info ---
                self.peers[peer_id] = {
                    'webrtcbin': webrtcbin, 'ice_agent': ice_agent_ref,
                    'viewer_pipeline': viewer_pipe,
                    'video_proxysink': v_psink, 'audio_proxysink': a_psink,
                    'video_tee': video_tee, 'audio_tee': audio_tee,
                    'video_tee_pad': video_tee_pad, 'audio_tee_pad': audio_tee_pad,
                    'video_pay': vpay,
                    'wb_video_sink': wb_video_sink,
                    'wb_audio_sink': wb_audio_sink,
                    'ice_candidates': [],
                }
                self.peers[peer_id]['signal_ids'] = [
                    webrtcbin.connect('on-ice-candidate', self._on_ice_candidate, peer_id),
                    webrtcbin.connect('notify::ice-connection-state', self._on_ice_state, peer_id),
                ]

                self._negotiate_sdp(peer_id, sdp_offer, answer_future, loop, host_ip)
            except Exception as e:
                import traceback
                logger.log(f"WHEP create_elements error: {e}\n{traceback.format_exc()}", level='ERROR')
                loop.call_soon_threadsafe(answer_future.set_result, None)
            return False

        GLib.idle_add(create_elements)

    def _negotiate_sdp(self, peer_id: str, sdp_offer: str, answer_future, loop, host_ip: str = None):
        """SDP negotiation on GLib thread — same pattern as pipelines/inputs/whip.py."""
        peer = self.peers.get(peer_id)
        if not peer:
            loop.call_soon_threadsafe(answer_future.set_result, None)
            return
        webrtcbin = peer['webrtcbin']

        # Step 1: set remote description (fire-and-forget)
        patched = patch_offer_h264_profile(sdp_offer)
        res, sdpmsg = GstSdp.SDPMessage.new_from_text(patched)
        if res != GstSdp.SDPResult.OK:
            logger.log("WHEP: failed to parse SDP offer", level='ERROR')
            self._cleanup_peer(peer_id)
            loop.call_soon_threadsafe(answer_future.set_result, None)
            return

        offer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)
        set_remote_promise = Gst.Promise.new()
        webrtcbin.emit('set-remote-description', offer, set_remote_promise)
        set_remote_promise.interrupt()

        # Step 2: create answer (callback fires when ready)
        def on_answer_created(answer_promise):
            try:
                reply = answer_promise.get_reply()
                answer_desc = reply.get_value('answer') if reply else None
                # GObject wrapper evaluates as falsy — must use `is None`
                if answer_desc is None:
                    logger.log(f"WHEP: no answer for peer {peer_id[:8]}", level='ERROR')
                    self._cleanup_peer(peer_id)
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return

                # Step 3: set local description (fire-and-forget) — triggers ICE gathering
                set_local_promise = Gst.Promise.new()
                webrtcbin.emit('set-local-description', answer_desc, set_local_promise)
                set_local_promise.interrupt()

                # Step 4: poll ICE gathering until complete
                poll_count = [0]

                def poll_ice_gathering():
                    poll_count[0] += 1
                    gathering_state = webrtcbin.get_property('ice-gathering-state')
                    if gathering_state == GstWebRTC.WebRTCICEGatheringState.COMPLETE or poll_count[0] >= 200:
                        self._resolve_sdp_answer(peer_id, host_ip, loop, answer_future)
                        return False
                    return True

                GLib.timeout_add(10, poll_ice_gathering)

            except Exception as e:
                import traceback
                logger.log(f"WHEP on_answer_created error: {e}\n{traceback.format_exc()}", level='ERROR')
                self._cleanup_peer(peer_id)
                loop.call_soon_threadsafe(answer_future.set_result, None)

        create_answer_promise = Gst.Promise.new_with_change_func(on_answer_created)
        webrtcbin.emit('create-answer', None, create_answer_promise)

    def _resolve_sdp_answer(self, peer_id: str, host_ip, loop, answer_future):
        """Build final SDP answer with ICE candidates. Called on GLib thread."""
        peer = self.peers.get(peer_id)
        if not peer:
            loop.call_soon_threadsafe(answer_future.set_result, None)
            return
        webrtcbin = peer['webrtcbin']

        local_desc = webrtcbin.get_property('local-description')
        if local_desc is None:
            loop.call_soon_threadsafe(answer_future.set_result, None)
            return

        sdp_text = local_desc.sdp.as_text()
        candidates = list(peer.get('ice_candidates', []))
        peer['ice_candidates'] = []
        sdp_text = inject_ice_candidates(sdp_text, candidates)
        if host_ip:
            sdp_text = rewrite_sdp_candidates(sdp_text, host_ip)

        loop.call_soon_threadsafe(answer_future.set_result, sdp_text)

    def _on_ice_state(self, webrtcbin, pspec, peer_id):
        try:
            state = webrtcbin.get_property("ice-connection-state")
            if state == GstWebRTC.WebRTCICEConnectionState.CONNECTED:
                # ICE transport up — force keyframe now so it's buffered when DTLS finishes
                peer = self.peers.get(peer_id)
                if peer and peer.get('video_pay'):
                    key_event = GstVideo.video_event_new_upstream_force_key_unit(
                        Gst.CLOCK_TIME_NONE, True, 0)
                    peer['video_pay'].send_event(key_event)
            elif state in (GstWebRTC.WebRTCICEConnectionState.FAILED,
                           GstWebRTC.WebRTCICEConnectionState.DISCONNECTED,
                           GstWebRTC.WebRTCICEConnectionState.CLOSED):
                # Defer cleanup — can't tear down webrtcbin from its own signal handler
                GLib.idle_add(self._deferred_cleanup, peer_id)
        except Exception as e:
            logger.log(f"Exception in _on_ice_state: {e}", level='ERROR')

    def _deferred_cleanup(self, peer_id):
        """Clean up a disconnected peer (called from GLib idle, not from signal handler)."""
        try:
            self._cleanup_peer(peer_id)
            for rid, (suid, rpid) in list(_resources.items()):
                if rpid == peer_id:
                    _resources.pop(rid, None)
            if not self.peers:
                _managers.pop(self.source_uid, None)
        except Exception as e:
            logger.log(f"Exception in _deferred_cleanup: {e}", level='ERROR')
        return False  # Don't repeat

    def _on_ice_candidate(self, webrtcbin, sdp_mline_index, candidate, peer_id):
        try:
            peer = self.peers.get(peer_id)
            if peer:
                peer['ice_candidates'].append({'sdpMLineIndex': sdp_mline_index, 'candidate': candidate})
        except Exception as e:
            logger.log(f"Exception in _on_ice_candidate: {e}", level='ERROR')

    def remove_peer(self, peer_id: str):
        self._cleanup_peer(peer_id)

    def _cleanup_peer(self, peer_id: str):
        """Remove per-viewer pipeline and proxysinks.

        Cleanup: READY (cleans ICE/DTLS) → release request pads → flush bus →
        remove webrtcbin from pipeline → NULL pipeline. All resources freed
        except the bare webrtcbin element (~52KB), kept in _orphaned_webrtcbins
        because libnice segfaults on GC finalize (use-after-free on ICE
        components freed during READY).
        """
        peer = self.peers.pop(peer_id, None)
        if not peer:
            return
        pipeline = get_pipeline()
        viewer_pipe = peer.get('viewer_pipeline')
        webrtcbin = peer.get('webrtcbin')
        name = viewer_pipe.get_name() if viewer_pipe else peer_id[:8]

        # 1. Disconnect signal handlers (break ref cycle)
        for sig_id in peer.get('signal_ids', []):
            try:
                if webrtcbin:
                    webrtcbin.handler_disconnect(sig_id)
            except Exception:
                pass
        peer.pop('ice_agent', None)

        # 2. Remove proxysinks from main pipeline
        for media in ('video', 'audio'):
            tee = peer.get(f'{media}_tee')
            tee_pad = peer.get(f'{media}_tee_pad')
            psink = peer.get(f'{media}_proxysink')
            if not (tee_pad and tee and psink and pipeline):
                continue
            sink_pad = psink.get_static_pad("sink")
            if sink_pad:
                peer_pad = sink_pad.get_peer()
                if peer_pad:
                    peer_pad.unlink(sink_pad)
            tee.release_request_pad(tee_pad)
            psink.set_state(Gst.State.NULL)
            if psink.get_parent() == pipeline:
                pipeline.remove(psink)

        # 3. READY viewer pipeline (graceful ICE/DTLS teardown)
        if viewer_pipe:
            viewer_pipe.set_state(Gst.State.READY)

        # 4. Unlink and release webrtcbin request pads (ICE already cleaned by READY)
        if webrtcbin:
            for pad_key in ('wb_video_sink', 'wb_audio_sink'):
                pad = peer.get(pad_key)
                if not pad:
                    continue
                peer_pad = pad.get_peer()
                if peer_pad:
                    peer_pad.unlink(pad)
                webrtcbin.release_request_pad(pad)

        # 5. Flush bus, remove webrtcbin, NULL pipeline.
        #    Keep webrtcbin ref — GC finalize segfaults on real ICE sessions.
        if viewer_pipe:
            bus = viewer_pipe.get_bus()
            if bus:
                bus.set_flushing(True)

        if viewer_pipe and webrtcbin:
            viewer_pipe.remove(webrtcbin)

        if viewer_pipe:
            viewer_pipe.set_state(Gst.State.NULL)

        if webrtcbin:
            _orphaned_webrtcbins.append(webrtcbin)

        logger.log(f"WHEP: {name} disposed (orphaned webrtcbins: {len(_orphaned_webrtcbins)})", level='INFO')


def _get_or_create_manager(source_uid: str) -> WebrtcPreviewManager:
    if source_uid not in _managers:
        _managers[source_uid] = WebrtcPreviewManager(source_uid)
    return _managers[source_uid]


# --- WHEP HTTP Endpoints ---

@router.post("/whep/{source_uid}")
async def whep_offer(source_uid: str, request: Request):
    # Auth: allow if auth disabled, user authenticated, or entity is in public_previews config
    if is_auth_enabled():
        user = await get_current_user_optional(request)
        if user is None:
            handler = request.app.state._state["pipeline_handler"]
            entity = handler.get_pipeline_by_uid(source_uid)
            if not entity or not config.is_public_preview(entity.data.name):
                raise HTTPException(status_code=401, detail="Not authenticated")

    content_type = request.headers.get("content-type", "")
    if "application/sdp" not in content_type:
        return Response(status_code=400, content="Content-Type must be application/sdp")

    sdp_offer = (await request.body()).decode("utf-8")
    peer_id = str(uuid.uuid4())
    resource_id = str(uuid.uuid4())
    host_ip = get_host_ip(request)
    _resources[resource_id] = (source_uid, peer_id)

    loop = asyncio.get_running_loop()
    answer_future = loop.create_future()
    manager = _get_or_create_manager(source_uid)
    manager.setup_peer(peer_id, sdp_offer, answer_future, loop, host_ip)

    try:
        answer = await asyncio.wait_for(answer_future, timeout=10.0)
    except asyncio.TimeoutError:
        _resources.pop(resource_id, None)
        return Response(status_code=500, content="WebRTC session setup timed out")
    if not answer:
        _resources.pop(resource_id, None)
        return Response(status_code=500, content="Failed to create WebRTC session")

    return Response(
        status_code=201, content=answer, media_type="application/sdp",
        headers={"Location": f"/whep/resource/{resource_id}", "Access-Control-Expose-Headers": "Location"},
    )


@router.patch("/whep/resource/{resource_id}")
async def whep_ice_candidate(resource_id: str, request: Request):
    if resource_id not in _resources:
        return Response(status_code=404)

    source_uid, peer_id = _resources[resource_id]
    content_type = request.headers.get("content-type", "")

    # Source switching: relink proxysink to different encoder tee
    if "application/json" in content_type:
        body = await request.json()
        new_source = body.get('source')
        if new_source:
            if is_auth_enabled():
                user = await get_current_user_optional(request)
                if user is None:
                    from pipeline_handler import HandlerSingleton
                    handler = HandlerSingleton()
                    new_entity = handler.get_pipeline_by_uid(new_source)
                    if not new_entity or not config.is_public_preview(new_entity.data.name):
                        return Response(status_code=401)

            loop = asyncio.get_running_loop()
            result_future = loop.create_future()

            def do_switch():
                try:
                    old_mgr = _managers.get(source_uid)
                    if not old_mgr or peer_id not in old_mgr.peers:
                        loop.call_soon_threadsafe(result_future.set_result, False)
                        return

                    # Find new source's preview encoders
                    new_mgr = _managers.get(new_source)
                    if not new_mgr:
                        # Create a temporary manager to find encoders
                        new_mgr = WebrtcPreviewManager(new_source)
                    new_video_enc, new_audio_enc = new_mgr._find_preview_encoders()
                    if not new_video_enc:
                        loop.call_soon_threadsafe(result_future.set_result, False)
                        return

                    new_video_tee = new_video_enc.tee
                    new_audio_tee = new_audio_enc.tee if new_audio_enc else None
                    if not new_video_tee:
                        loop.call_soon_threadsafe(result_future.set_result, False)
                        return

                    peer = old_mgr.peers[peer_id]

                    # Swap tee pads for each media type (audio optional)
                    swap_list = [('video', new_video_tee)]
                    if new_audio_tee:
                        swap_list.append(('audio', new_audio_tee))
                    for media, new_tee in swap_list:
                        old_tee = peer.get(f'{media}_tee')
                        old_pad = peer.get(f'{media}_tee_pad')
                        psink = peer.get(f'{media}_proxysink')
                        if not (old_tee and old_pad and psink):
                            continue

                        # Unlink old
                        sink_pad = psink.get_static_pad("sink")
                        if sink_pad:
                            peer_pad = sink_pad.get_peer()
                            if peer_pad:
                                peer_pad.unlink(sink_pad)
                        old_tee.release_request_pad(old_pad)

                        # Link new
                        new_pad = new_tee.request_pad_simple("src_%u")
                        new_pad.link(sink_pad)

                        # Update peer refs
                        peer[f'{media}_tee'] = new_tee
                        peer[f'{media}_tee_pad'] = new_pad

                    # Request keyframe for fast display
                    vpay = peer.get('video_pay')
                    if vpay:
                        key_event = GstVideo.video_event_new_upstream_force_key_unit(
                            Gst.CLOCK_TIME_NONE, True, 0)
                        vpay.send_event(key_event)

                    # Disconnect old signal handlers (they reference old_mgr via bound methods)
                    webrtcbin = peer.get('webrtcbin')
                    for sig_id in peer.get('signal_ids', []):
                        try:
                            if webrtcbin:
                                webrtcbin.handler_disconnect(sig_id)
                        except Exception:
                            pass

                    # Move peer from old manager to new/existing manager
                    old_mgr.peers.pop(peer_id, None)
                    if not old_mgr.peers:
                        _managers.pop(source_uid, None)

                    if new_source not in _managers:
                        _managers[new_source] = WebrtcPreviewManager(new_source)
                    target_mgr = _managers[new_source]
                    target_mgr.peers[peer_id] = peer

                    # Reconnect signal handlers to new manager
                    if webrtcbin:
                        peer['signal_ids'] = [
                            webrtcbin.connect('on-ice-candidate', target_mgr._on_ice_candidate, peer_id),
                            webrtcbin.connect('notify::ice-connection-state', target_mgr._on_ice_state, peer_id),
                        ]

                    # Update resource mapping
                    _resources[resource_id] = (new_source, peer_id)

                    logger.log(f"WHEP: switched {peer_id[:8]} from {source_uid[:8]} to {new_source[:8]}", level='INFO')
                    loop.call_soon_threadsafe(result_future.set_result, True)
                except Exception as e:
                    logger.log(f"WHEP switch error: {e}", level='ERROR')
                    loop.call_soon_threadsafe(result_future.set_result, False)

            bridge.run_sync_in_glib(do_switch)
            success = await result_future
            return Response(status_code=204 if success else 500)

    # ICE trickle candidates
    if "application/trickle-ice-sdpfrag" in content_type:
        body = (await request.body()).decode("utf-8")
        sdp_mline_index = 0
        for line in body.strip().split("\n"):
            line = line.strip()
            if line.startswith("a=mid:"):
                try:
                    sdp_mline_index = int(line[6:])
                except (ValueError, TypeError):
                    sdp_mline_index = 0
        for line in body.strip().split("\n"):
            line = line.strip()
            if line.startswith("a=ice-candidate:"):
                candidate = line[2:]

                def do_add(c=candidate, idx=sdp_mline_index):
                    mgr = _managers.get(source_uid)
                    if mgr and (peer := mgr.peers.get(peer_id)):
                        peer['webrtcbin'].emit('add-ice-candidate', idx, c)

                bridge.run_sync_in_glib(do_add)

    return Response(status_code=204)


@router.delete("/whep/resource/{resource_id}")
async def whep_delete(resource_id: str):
    mapping = _resources.pop(resource_id, None)
    if not mapping:
        return Response(status_code=404)

    source_uid, peer_id = mapping
    loop = asyncio.get_running_loop()
    done = loop.create_future()

    def do_remove():
        try:
            manager = _managers.get(source_uid)
            if manager:
                manager.remove_peer(peer_id)
                if not manager.peers:
                    _managers.pop(source_uid, None)
        except Exception as e:
            logger.log(f"WHEP delete error: {e}", level='ERROR')
        loop.call_soon_threadsafe(done.set_result, True)

    bridge.run_sync_in_glib(do_remove)
    await done
    return Response(status_code=200)


@router.options("/whep/{source_uid}")
@router.options("/whep/resource/{resource_id}")
async def whep_options(source_uid: str = "", resource_id: str = ""):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })
