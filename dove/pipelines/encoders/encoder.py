from typing import Optional
from gi.repository import Gst, GLib

from dove.api.encoder_models import EncoderEntityDTO, EncoderUpdateDTO
from dove.api.input_models import AudioFilterDTO
from dove.api.helper import get_encoder_dto_class
from dove.event_loop_bridge import safe_broadcast
from dove.logger import logger
from dove.pipelines.base import GSTBase
from dove.pipelines.audio_filters import (
    FILTER_ELEMENT_MAP,
    update_filter_params,
    rebuild_between_anchors,
)
from dove.config_handler import ConfigReader

config = ConfigReader()


class Encoder(GSTBase):
    """Encoder entity — encodes a source stream and exposes a tee for consumers.

    Audio encoders support a per-encoder filter chain (between identity anchors
    af_enc_in_<uid> / af_enc_out_<uid>) so loudness normalization can be applied
    to the encoded output without affecting the live preview path.
    """
    data: EncoderEntityDTO
    tee: Optional[Gst.Element] = None
    _bin: Optional[Gst.Bin] = None
    core_pipeline: Optional[Gst.Pipeline] = None

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

        # Preview FPS via videorate max-rate (runtime tunable, no caps renegotiation)
        max_rate = None
        if is_preview and self.data.framerate:
            try:
                max_rate = int(self.data.framerate.split('/')[0])
            except (ValueError, IndexError):
                max_rate = None

        # Caps
        caps_parts = [f"video/x-raw,format={fmt}"]
        if self.data.width:
            caps_parts.append(f"width={self.data.width}")
        if self.data.height and not is_preview:
            caps_parts.append(f"height={self.data.height}")
        if is_preview:
            caps_parts.append("pixel-aspect-ratio=1/1")
        if self.data.framerate and not is_preview:
            caps_parts.append(f"framerate={self.data.framerate}")
        caps_str = ",".join(caps_parts)

        videorate_str = "videorate skip-to-first=true"
        if max_rate is not None:
            videorate_str = f"videorate skip-to-first=true max-rate={max_rate}"

        # Encoder element + options
        opts = (self.data.options or '').strip()
        enc_str = f"{self.data.element} {opts}".strip()

        # Profile caps (explicit capsfilter for parse_bin_from_description compatibility)
        profile_str = ""
        if self.data.profile and self.data.codec:
            profile_str = f"capsfilter caps=\"video/x-{self.data.codec},profile={self.data.profile}\""

        # Build pipeline
        use_vapostproc = pre.startswith("vapostproc") if pre else False
        parts = [
            f"queue name=enc_queue_{uid} leaky=upstream max-size-buffers=1",
            # ts-offset set by paired audio encoder when filters add latency
            f"identity name=video_delay_{uid} ts-offset=0",
        ]
        if use_vapostproc:
            # GPU path: vapostproc handles format conversion + scaling
            parts.extend([
                pre,
                videorate_str,
                caps_str,
            ])
        else:
            # CPU path: standard videoconvert + videoscale
            parts.extend([
                "videoconvert", "videoscale", videorate_str,
                caps_str,
            ])
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

        # Audio filter chain anchors: identity elements that stay in place forever.
        # At startup the chain between them is empty (direct link); rebuild_between_anchors
        # re-populates it when the user adds/removes filters via the API.
        # These anchors are only rendered for non-preview audio encoders (preview path
        # stays at zero latency — no filter chain).
        is_preview = getattr(self.data, 'is_preview', False)
        use_filters = not is_preview

        parts = [
            # 4s headroom: covers audioloudnorm 3s lookahead warmup
            f"queue name=enc_queue_{uid} max-size-time=4000000000 max-size-buffers=0 max-size-bytes=0",
            "audioconvert", "audioresample",
        ]

        if use_filters:
            # Normalize to pipeline format before the filter anchors so filter chain
            # always gets consistent input. The filter chain output is re-normalized
            # to the same format by the post-anchor audioconvert+audioresample.
            parts.append(
                f"audio/x-raw,format=F32LE,layout=interleaved,"
                f"rate={config.get_default_audio_rate()},"
                f"channels={config.get_default_audio_channels()}"
            )
            parts.append(f"identity name=af_enc_in_{uid} silent=true")
            parts.append(f"identity name=af_enc_out_{uid} silent=true")
            parts.append("audioconvert")
            parts.append("audioresample")

        if fmt:
            # Final format caps required by the encoder element (e.g. S16LE for opusenc/fdkaacenc)
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

    def _latency_query_probe(self, pad, info):
        """Block latency queries from propagating upstream through encoder branches."""
        query = info.get_query()
        if query.type == Gst.QueryType.LATENCY:
            logger.log(f"Encoder {self.data.uid}: blocked latency query", level='DEBUG')
            return Gst.PadProbeReturn.HANDLED
        return Gst.PadProbeReturn.OK

    def install_latency_firewall(self):
        """Prevent encoder-internal latency from affecting pipeline-wide latency."""
        if not self._bin:
            return
        sink_pad = self._bin.get_static_pad("sink")
        if sink_pad:
            sink_pad.add_probe(Gst.PadProbeType.QUERY_UPSTREAM, self._latency_query_probe)

    def check_state(self):
        if not self._bin:
            return
        _, state, _ = self._bin.get_state(0)
        state_name = Gst.Element.state_get_name(state)
        if self.data.state != state_name:
            self.data.state = state_name
            safe_broadcast("UPDATE", self.data, type="encoder")
        if (self.data.type == "audio"
                and not getattr(self.data, 'is_preview', False)
                and not getattr(self, '_latency_compensation_done', False)
                and state == Gst.State.PLAYING):
            self._latency_compensation_done = True
            self._apply_filter_latency_compensation()

    def attach(self, pipeline: Gst.Pipeline):
        uid = self.data.uid
        self.core_pipeline = pipeline
        self._bin = None
        self.tee = pipeline.get_by_name(f"enc_tee_{uid}")
        self._latency_compensation_done = False

    def _find_element(self, name):
        """Find a named element in bin or core pipeline."""
        elem = None
        if self._bin:
            elem = self._bin.get_by_name(name)
        if not elem and self.core_pipeline:
            elem = self.core_pipeline.get_by_name(name)
        return elem

    async def update(self, data):
        """Handle runtime update — name changes, audio filter chain edits."""
        if not isinstance(data, EncoderUpdateDTO):
            data = EncoderUpdateDTO.model_validate(data)
        if data.name is not None:
            self.data.name = data.name
        if data.audio_filters is not None:
            if self.data.type != "audio":
                logger.log(f"Encoder {self.data.uid}: audio_filters update ignored on video encoder", level='WARNING')
            elif getattr(self.data, 'is_preview', False):
                logger.log(f"Encoder {self.data.uid}: audio_filters update ignored on preview encoder", level='WARNING')
            else:
                self._update_audio_filters(data.audio_filters)
        safe_broadcast("UPDATE", self.data, type="encoder")

    def _update_audio_filters(self, new_filters: list[AudioFilterDTO]):
        """Apply audio filter changes on the running pipeline. Mirrors Input._update_audio_filter_params."""
        uid = self.data.uid
        old_filters = self.data.audio_filters or []

        structure_match = (
            len(new_filters) == len(old_filters) and
            all(n.type == o.type and n.enabled == o.enabled
                for n, o in zip(new_filters, old_filters))
        )

        if structure_match:
            def do_update_params():
                update_filter_params(
                    new_filters, self._find_element, uid,
                    anchor_in=f"af_enc_in_{uid}", anchor_out=f"af_enc_out_{uid}",
                )
                self._apply_filter_latency_compensation()
                return False
            GLib.idle_add(do_update_params)
        else:
            GLib.idle_add(self._rebuild_audio_filter_chain, new_filters)

        self.data.audio_filters = new_filters

    def _rebuild_audio_filter_chain(self, new_filters):
        """Replace audio filter elements between the encoder's af_enc_in/af_enc_out anchors."""
        uid = self.data.uid
        af_in = self._find_element(f"af_enc_in_{uid}")
        af_out = self._find_element(f"af_enc_out_{uid}")
        if not af_in or not af_out:
            logger.log(f"Encoder {uid}: filter anchors missing (in={af_in is not None}, out={af_out is not None})", level='ERROR')
            return False
        pipe = af_in.get_parent()
        rebuild_between_anchors(
            af_in, af_out, new_filters, uid, pipe,
            element_map=FILTER_ELEMENT_MAP, audio=True, allow_rate_conversion=True,
        )
        self._apply_filter_latency_compensation()
        return False

    def _apply_filter_latency_compensation(self):
        if getattr(self.data, 'is_preview', False):
            return
        af_out = self._bin.get_by_name(f"af_enc_out_{self.data.uid}") if self._bin else None
        if not af_out:
            return
        sink = af_out.get_static_pad("sink")
        if not sink:
            return

        def _on_first_buffer(pad, info, _data):
            try:
                q = Gst.Query.new_latency()
                if pad.peer_query(q):
                    _live, min_lat, _max_lat = q.parse_latency()
                    GLib.idle_add(self._set_paired_video_offset, int(min_lat))
            except Exception as e:
                logger.log(f"Latency probe failed for encoder {self.data.uid}: {e}", level='WARNING')
            return Gst.PadProbeReturn.REMOVE

        sink.add_probe(Gst.PadProbeType.BUFFER, _on_first_buffer, None)

    def _set_paired_video_offset(self, ts_offset_ns):
        from dove.pipeline_handler import HandlerSingleton
        handler = HandlerSingleton()
        audio_uid = self.data.uid
        video_uid = None
        for o in handler.get_pipelines("outputs") or []:
            if getattr(o.data, 'audio_encoder', None) == audio_uid:
                video_uid = getattr(o.data, 'video_encoder', None)
                break
        if not video_uid:
            return False
        pipeline = self._bin.get_parent() if self._bin else None
        delay = pipeline.get_by_name(f"video_delay_{video_uid}") if pipeline else None
        if delay:
            delay.set_property("ts-offset", ts_offset_ns)
            logger.log(f"Encoder {audio_uid}: applied video ts-offset={ts_offset_ns}ns to {video_uid}", level='INFO')
        return False
