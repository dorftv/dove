from typing import Optional
from gi.repository import Gst

from api.encoder_models import EncoderEntityDTO
from api.helper import get_encoder_dto_class
from event_loop_bridge import safe_broadcast
from pipelines.base import GSTBase
from config_handler import ConfigReader

config = ConfigReader()


class Encoder(GSTBase):
    """Encoder entity — encodes a source stream and exposes a tee for consumers."""
    data: EncoderEntityDTO
    tee: Optional[Gst.Element] = None
    _bin: Optional[Gst.Bin] = None

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid
        if self.data.type == "video":
            return self._build_video_str(uid)
        else:
            return self._build_audio_str(uid)

    def _build_video_str(self, uid) -> str:
        cls = get_encoder_dto_class(self.data.element)
        fmt = getattr(cls, 'format', 'I420') if cls else 'I420'
        pre = getattr(cls, 'pre_elements', '') if cls else ''
        mid = getattr(cls, 'mid_elements', '') if cls else ''
        post = getattr(cls, 'post_elements', '') if cls else ''

        # Preview encoders: omit height so GStreamer preserves input aspect ratio
        is_preview = getattr(self.data, 'is_preview', False)

        # Caps
        caps_parts = [f"video/x-raw,format={fmt}"]
        if self.data.width:
            caps_parts.append(f"width={self.data.width}")
        if self.data.height and not is_preview:
            caps_parts.append(f"height={self.data.height}")
        if is_preview:
            caps_parts.append("pixel-aspect-ratio=1/1")
        if self.data.framerate:
            caps_parts.append(f"framerate={self.data.framerate}")
        caps_str = ",".join(caps_parts)

        # Encoder element + options
        opts = (self.data.options or '').strip()
        enc_str = f"{self.data.element} {opts}".strip()

        # Profile caps (explicit capsfilter for parse_bin_from_description compatibility)
        profile_str = ""
        if self.data.profile and self.data.codec:
            profile_str = f"capsfilter caps=\"video/x-{self.data.codec},profile={self.data.profile}\""

        # Build pipeline
        # videoscale add-borders defaults to true in GStreamer 1.28 — preserves aspect ratio
        vscale = "videoscale"
        parts = [
            f"queue name=enc_queue_{uid} leaky=upstream max-size-buffers=1",
            "videoconvert", vscale, "videorate skip-to-first=true",
            caps_str,
        ]
        if pre:
            parts.append(pre)
        parts.append(enc_str)
        if mid:
            parts.append(mid)
        if profile_str:
            parts.append(profile_str)
        if post:
            parts.append(post)
        return " ! ".join(parts)

    def _build_audio_str(self, uid) -> str:
        cls = get_encoder_dto_class(self.data.element)
        fmt = getattr(cls, 'format', 'S16LE') if cls else 'S16LE'
        pre = getattr(cls, 'pre_elements', '') if cls else ''
        post = getattr(cls, 'post_elements', '') if cls else ''

        parts = [
            f"queue name=enc_queue_{uid} max-size-time=200000000 max-size-buffers=0 max-size-bytes=0",
            "audioconvert", "audioresample",
        ]

        if fmt:
            caps_str = (
                f"audio/x-raw,format={fmt},layout=interleaved,"
                f"rate={config.get_default_audio_rate()},"
                f"channels={config.get_default_audio_channels()}"
            )
            parts.append(caps_str)

        if pre:
            parts.append(pre)

        opts = (self.data.options or '').strip()
        parts.append(f"{self.data.element} {opts}".strip())

        if post:
            parts.append(post)

        return " ! ".join(parts)

    def check_state(self):
        if not self._bin:
            return
        _, state, _ = self._bin.get_state(0)
        state_name = Gst.Element.state_get_name(state)
        if self.data.state != state_name:
            self.data.state = state_name
            safe_broadcast("UPDATE", self.data, type="encoder")

    def attach(self, pipeline: Gst.Pipeline):
        uid = self.data.uid
        self._bin = None
        self.tee = pipeline.get_by_name(f"enc_tee_{uid}")
