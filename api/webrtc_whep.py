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
import time
import uuid
import threading
from fastapi import APIRouter, Request, Response

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
from event_loop_bridge import bridge
from logger import logger

router = APIRouter()

_managers: dict[str, "WebrtcPreviewManager"] = {}  # source_uid -> manager
_resources: dict[str, tuple[str, str]] = {}  # resource_id -> (source_uid, peer_id)
# GC finalize on webrtcbin that had real ICE sessions segfaults in libnice.
# Keep refs alive (~52KB each). Pipeline and all other resources are fully freed.
_orphaned_webrtcbins: list = []



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
        """Create per-viewer elements on GLib thread, SDP negotiation on worker thread."""
        elements_ready = threading.Event()
        setup_ok = [False]

        def create_elements(attempt=0):
            try:
                logger.log(f"WHEP create_elements attempt={attempt} for {self.source_uid[:8]}", level='WARNING')
                video_enc, audio_enc = self._find_preview_encoders()
                if not video_enc or not audio_enc:
                    if attempt < 10:
                        GLib.timeout_add(200, lambda a=attempt+1: create_elements(a) or False)
                        return False
                    logger.log(f"WHEP: no preview encoders for {self.source_uid}", level='ERROR')
                    elements_ready.set()
                    return False

                video_tee = video_enc.tee
                audio_tee = audio_enc.tee
                if not video_tee or not audio_tee:
                    logger.log(f"WHEP: encoder tees not available", level='ERROR')
                    elements_ready.set()
                    return False

                pipeline = get_pipeline()
                pid = peer_id[:8]

                # --- Create proxysinks in main pipeline ---
                v_psink = Gst.ElementFactory.make("proxysink", f"psink_v_{pid}")
                a_psink = Gst.ElementFactory.make("proxysink", f"psink_a_{pid}")
                for ps in (v_psink, a_psink):
                    pipeline.add(ps)
                    ps.sync_state_with_parent()

                video_tee_pad = video_tee.request_pad_simple("src_%u")
                audio_tee_pad = audio_tee.request_pad_simple("src_%u")
                video_tee_pad.link(v_psink.get_static_pad("sink"))
                audio_tee_pad.link(a_psink.get_static_pad("sink"))

                # --- Create viewer pipeline ---
                viewer_pipe = Gst.Pipeline.new(f"viewer_{pid}")
                viewer_pipe.use_clock(pipeline.get_clock())
                viewer_pipe.set_base_time(pipeline.get_base_time())
                viewer_pipe.set_start_time(Gst.CLOCK_TIME_NONE)

                # --- Create proxysrc elements ---
                v_psrc = Gst.ElementFactory.make("proxysrc", f"psrc_v_{pid}")
                a_psrc = Gst.ElementFactory.make("proxysrc", f"psrc_a_{pid}")
                v_psrc.set_property("proxysink", v_psink)
                a_psrc.set_property("proxysink", a_psink)

                # --- Create webrtcbin ---
                webrtcbin = Gst.ElementFactory.make("webrtcbin", f"wb_{pid}")
                if not webrtcbin:
                    elements_ready.set()
                    return False

                ice_agent_ref = configure_webrtcbin(webrtcbin)
                webrtcbin.set_property("latency", 50)

                # --- Create per-viewer elements ---
                video_pt, audio_pt = _extract_offer_pts(sdp_offer)

                vq = Gst.ElementFactory.make("queue", f"pvq_{pid}")
                vq.set_property("leaky", 2)
                vq.set_property("max-size-buffers", 1)
                vpay = Gst.ElementFactory.make("rtph264pay", f"vpay_{pid}")
                vpay.set_property("config-interval", -1)
                vpay.set_property("aggregate-mode", 1)
                if video_pt:
                    vpay.set_property("pt", video_pt)

                aq = Gst.ElementFactory.make("queue", f"paq_{pid}")
                aq.set_property("leaky", 2)
                aq.set_property("max-size-buffers", 1)
                apay = Gst.ElementFactory.make("rtpopuspay", f"apay_{pid}")
                if audio_pt:
                    apay.set_property("pt", audio_pt)

                # --- Add all to viewer pipeline ---
                for e in (v_psrc, vq, vpay, a_psrc, aq, apay, webrtcbin):
                    viewer_pipe.add(e)

                # --- Link chains ---
                v_psrc.link(vq)
                vq.link(vpay)
                a_psrc.link(aq)
                aq.link(apay)
                wb_video_sink = webrtcbin.request_pad_simple("sink_%u")
                wb_audio_sink = webrtcbin.request_pad_simple("sink_%u")
                vpay.get_static_pad("src").link(wb_video_sink)
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
                setup_ok[0] = True
                elements_ready.set()
            except Exception as e:
                import traceback
                logger.log(f"WHEP create_elements error: {e}\n{traceback.format_exc()}", level='ERROR')
                elements_ready.set()
            return False

        def sdp_worker():
            try:
                got_it = elements_ready.wait(timeout=5)
                if not setup_ok[0]:
                    # Test if GLib is responsive
                    glib_probe = threading.Event()
                    GLib.idle_add(lambda: glib_probe.set() or False)
                    glib_alive = glib_probe.wait(timeout=2)
                    logger.log(f"WHEP sdp_worker: elements not ready (waited={got_it}, glib_alive={glib_alive}) for {self.source_uid[:8]}", level='ERROR')
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return

                peer = self.peers.get(peer_id)
                if not peer:
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return
                webrtcbin = peer['webrtcbin']

                # 1. Set remote description
                patched = patch_offer_h264_profile(sdp_offer)
                res, sdpmsg = GstSdp.SDPMessage.new_from_text(patched)
                if res != GstSdp.SDPResult.OK:
                    logger.log(f"WHEP: failed to parse SDP offer", level='ERROR')
                    GLib.idle_add(lambda: self._cleanup_peer(peer_id) or False)
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return

                offer = GstWebRTC.WebRTCSessionDescription.new(GstWebRTC.WebRTCSDPType.OFFER, sdpmsg)
                promise = Gst.Promise.new()
                webrtcbin.emit('set-remote-description', offer, promise)
                promise.wait()

                # 2. Create answer
                promise = Gst.Promise.new()
                webrtcbin.emit('create-answer', None, promise)
                promise.wait()
                reply = promise.get_reply()
                if not reply or not reply.get_value('answer'):
                    logger.log(f"WHEP: no answer for peer {peer_id[:8]}", level='ERROR')
                    GLib.idle_add(lambda: self._cleanup_peer(peer_id) or False)
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return

                # 3. Set local description (triggers ICE gathering)
                answer = reply.get_value('answer')
                promise = Gst.Promise.new()
                webrtcbin.emit('set-local-description', answer, promise)
                promise.wait()

                # 4. Wait for ICE gathering (poll at 10ms for fast response)
                for _ in range(200):
                    if webrtcbin.get_property('ice-gathering-state') == GstWebRTC.WebRTCICEGatheringState.COMPLETE:
                        break
                    time.sleep(0.01)

                # 5. Build final SDP answer
                local_desc = webrtcbin.get_property('local-description')
                if not local_desc:
                    loop.call_soon_threadsafe(answer_future.set_result, None)
                    return

                sdp_text = local_desc.sdp.as_text()
                peer = self.peers.get(peer_id)
                candidates = list(peer.get('ice_candidates', [])) if peer else []
                if peer:
                    peer['ice_candidates'] = []
                sdp_text = inject_ice_candidates(sdp_text, candidates)
                if host_ip:
                    sdp_text = rewrite_sdp_candidates(sdp_text, host_ip)

                loop.call_soon_threadsafe(answer_future.set_result, sdp_text)

            except Exception as e:
                import traceback
                logger.log(f"WHEP sdp_worker error: {e}\n{traceback.format_exc()}", level='ERROR')
                GLib.idle_add(lambda: self._cleanup_peer(peer_id) or False)
                loop.call_soon_threadsafe(answer_future.set_result, None)

        GLib.idle_add(create_elements)
        threading.Thread(target=sdp_worker, daemon=True).start()

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

        logger.log(f"WHEP: {name} disposed (orphaned webrtcbins: {len(_orphaned_webrtcbins)})", level='WARNING')


def _get_or_create_manager(source_uid: str) -> WebrtcPreviewManager:
    if source_uid not in _managers:
        _managers[source_uid] = WebrtcPreviewManager(source_uid)
    return _managers[source_uid]


# --- WHEP HTTP Endpoints ---

@router.post("/whep/{source_uid}")
async def whep_offer(source_uid: str, request: Request):
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
                    if not new_video_enc or not new_audio_enc:
                        loop.call_soon_threadsafe(result_future.set_result, False)
                        return

                    new_video_tee = new_video_enc.tee
                    new_audio_tee = new_audio_enc.tee
                    if not new_video_tee or not new_audio_tee:
                        loop.call_soon_threadsafe(result_future.set_result, False)
                        return

                    peer = old_mgr.peers[peer_id]

                    # Swap tee pads for each media type
                    for media, new_tee in [('video', new_video_tee), ('audio', new_audio_tee)]:
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

                    # Move peer from old manager to new/existing manager
                    old_mgr.peers.pop(peer_id, None)
                    if not old_mgr.peers:
                        _managers.pop(source_uid, None)

                    if new_source not in _managers:
                        _managers[new_source] = WebrtcPreviewManager(new_source)
                    _managers[new_source].peers[peer_id] = peer

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
                except ValueError:
                    pass
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
