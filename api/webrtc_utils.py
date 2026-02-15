"""Shared WebRTC utilities for WHEP (preview) and WHIP (ingest)."""

import os
import re
import socket
from urllib.parse import urlparse

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')
from gi.repository import Gst, GstWebRTC

from config_handler import ConfigReader

config = ConfigReader()

_LOOPBACK = ("", "localhost", "127.0.0.1", "::1")


def get_host_ip(request) -> str | None:
    """Determine external IP for SDP candidates.
    Priority: ANNOUNCED_IP env > config > Origin/X-Forwarded-Host > None.
    """
    env_ip = os.environ.get('ANNOUNCED_IP')
    if env_ip:
        return env_ip

    announced = config.get_webrtc_config().get('announced_ip')
    if announced:
        return announced

    for header in ("origin", "x-forwarded-host"):
        val = request.headers.get(header, "")
        if not val:
            continue
        hostname = urlparse(val).hostname if "://" in val else val.split(":")[0]
        if hostname and hostname not in _LOOPBACK:
            try:
                return socket.gethostbyname(hostname)
            except socket.gaierror:
                return hostname
    return None


def get_container_ip() -> str | None:
    """Determine container's outbound IP (no traffic sent, UDP connect trick)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return None


def rewrite_sdp_candidates(sdp_text: str, host_ip: str) -> str:
    """Replace Docker internal IPs in ICE candidates with host IP."""
    container_ip = get_container_ip()
    if not container_ip or container_ip == host_ip:
        return sdp_text
    return sdp_text.replace(container_ip, host_ip)


def patch_offer_h264_profile(sdp_offer: str) -> str:
    """Rewrite H264 profile-level-id in offer to match our encoder (42c01e).
    Needed for GStreamer webrtcbin caps intersection.
    """
    return re.sub(
        r'profile-level-id=4[02][ecd0][01][12][0-9a-f]',
        'profile-level-id=42c01e',
        sdp_offer, flags=re.IGNORECASE,
    )


def inject_ice_candidates(sdp_text: str, candidates: list[dict]) -> str:
    """Inject gathered ICE candidates into SDP answer."""
    cand_lines = [f"a={c['candidate']}" for c in candidates if c.get('candidate')]
    if not cand_lines:
        return sdp_text
    insert = "\r\n".join(cand_lines) + "\r\n"
    if "a=end-of-candidates" in sdp_text:
        return sdp_text.replace("a=end-of-candidates", insert + "a=end-of-candidates", 1)
    return sdp_text.rstrip() + "\r\n" + insert


def get_pipeline():
    """Return the main GStreamer pipeline from the handler singleton."""
    from pipeline_handler import HandlerSingleton
    return HandlerSingleton().core_pipeline.pipeline


def configure_webrtcbin(webrtcbin) -> object | None:
    """Apply STUN/TURN/port config to a webrtcbin element.
    Returns ICE agent ref (or None) for port config lifetime.
    """
    webrtc_config = config.get_webrtc_config()

    webrtcbin.set_property("bundle-policy", GstWebRTC.WebRTCBundlePolicy.MAX_BUNDLE)

    stun = webrtc_config.get('stun_server')
    if stun:
        webrtcbin.set_property("stun-server", stun)
    turn = webrtc_config.get('turn_server')
    if turn and webrtc_config.get('turn_user'):
        url = turn.replace("turn://", f"turn://{webrtc_config['turn_user']}:{webrtc_config.get('turn_password', '')}@")
        webrtcbin.set_property("turn-server", url)

    ice_agent_ref = None
    min_port = webrtc_config.get('min_rtp_port', 0)
    max_port = webrtc_config.get('max_rtp_port', 0)
    if min_port and max_port:
        ice_agent_ref = webrtcbin.get_property("ice-agent")
        if ice_agent_ref:
            ice_agent_ref.set_property("min-rtp-port", min_port)
            ice_agent_ref.set_property("max-rtp-port", max_port)

    return ice_agent_ref
