from abc import ABC, abstractmethod
from uuid import UUID, uuid4
from typing import Union, Optional

from pipelines.base import GSTBase
from api.input_models import InputDTO, SuccessDTO, InputDeleteDTO, updateInputDTO, AudioFilterDTO, VideoFilterDTO
from pipelines.audio_filters import build_audio_filter_str, update_filter_params, rebuild_between_anchors
from pipelines.video_filters import build_video_filter_str, VIDEO_FILTER_ELEMENT_MAP
from gi.repository import Gst, GLib

from event_loop_bridge import bridge, safe_broadcast
from logger import logger


class Input(GSTBase, ABC):
    data: InputDTO
    core_pipeline: Optional[Gst.Pipeline] = None
    video_tee: Optional[Gst.Element] = None
    audio_tee: Optional[Gst.Element] = None
    input_videomixer: Optional[Gst.Element] = None
    input_audiomixer: Optional[Gst.Element] = None
    volume_element: Optional[Gst.Element] = None
    _bin: Optional[Gst.Bin] = None  # For dynamic addition

    def get_video_end(self) -> str:
        uid = self.data.uid
        caps = self.get_caps('video')
        add_borders = "true" if getattr(self.data, 'fit', True) else "false"
        filters = getattr(self.data, 'video_filters', None) or []
        filter_str = build_video_filter_str(uid, filters)
        return (
            f" videorate skip-to-first=true ! videoconvert ! videoscale name=videoscale_out_{uid} add-borders={add_borders} ! {caps} ! "
            f" {filter_str} ! "
            f" tee name=video_tee_{uid} allow-not-linked=true "
        )

    def get_audio_end(self) -> str:
        uid = self.data.uid
        caps = self.get_caps('audio')
        filters = getattr(self.data, 'audio_filters', None) or []
        filter_str = build_audio_filter_str(uid, filters)
        return (
            f" volume name=volume_{uid} volume={self.data.volume}"
            f" ! {filter_str} ! "
            f" audiorate skip-to-first=true ! audioresample ! {caps} ! "
            f" level name=level_{uid} interval=200000000 post-messages=true ! "
            f" tee name=audio_tee_{uid} allow-not-linked=true "
        )

    # For single-pipeline architecture
    @abstractmethod
    def build_pipeline_str(self) -> str:
        """Return pipeline string fragment for this input. Override in subclasses."""
        pass

    def attach(self, pipeline: Gst.Pipeline):
        """Get element references after pipeline is created."""
        uid = self.data.uid
        self.core_pipeline = pipeline
        self._bin = None  # Clear stale bin reference after rebuild
        self.video_tee = pipeline.get_by_name(f"video_tee_{uid}")
        self.audio_tee = pipeline.get_by_name(f"audio_tee_{uid}")
        self.input_videomixer = pipeline.get_by_name(f"input_videomixer_{uid}")
        self.input_audiomixer = pipeline.get_by_name(f"input_audiomixer_{uid}")
        self.volume_element = pipeline.get_by_name(f"volume_{uid}")
        logger.log(f"Input {uid} attach: video_tee={'found' if self.video_tee else 'NOT FOUND'}, audio_tee={'found' if self.audio_tee else 'NOT FOUND'}, volume={'found' if self.volume_element else 'NOT FOUND'}, videomixer={'found' if self.input_videomixer else 'NOT FOUND'}", level='DEBUG')

    def attach_to_bin(self, bin: Gst.Bin):
        """Get element references from within a bin (for dynamic addition)."""
        uid = self.data.uid
        self.video_tee = bin.get_by_name(f"video_tee_{uid}")
        self.audio_tee = bin.get_by_name(f"audio_tee_{uid}")
        self.input_videomixer = bin.get_by_name(f"input_videomixer_{uid}")
        self.input_audiomixer = bin.get_by_name(f"input_audiomixer_{uid}")
        self.volume_element = bin.get_by_name(f"volume_{uid}")
        logger.log(f"Input {uid} attach_to_bin: video_tee={'found' if self.video_tee else 'NOT FOUND'}, audio_tee={'found' if self.audio_tee else 'NOT FOUND'}, videomixer={'found' if self.input_videomixer else 'NOT FOUND'}", level='DEBUG')

    def seek_to_position(self, position):
        pipeline = self.get_pipeline()
        if not pipeline:
            logger.log(f"Seek failed for {self.data.uid}: no pipeline", level='WARNING')
            return

        position_ns = position * Gst.SECOND

        def do_seek():
            try:
                seek_event = Gst.Event.new_seek(
                    1.0, Gst.Format.TIME,
                    Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                    Gst.SeekType.SET, position_ns,
                    Gst.SeekType.NONE, 0)
                result = pipeline.send_event(seek_event)
                logger.log(f"Seek {self.data.uid} to {position}s: {'ok' if result else 'failed'}", level='DEBUG')
            except Exception as e:
                logger.log(f"Exception in do_seek for {self.data.uid}: {e}", level='ERROR')
            return False  # Don't repeat

        GLib.idle_add(do_seek)

    def _find_element(self, name):
        """Find a named element in bin or core pipeline."""
        elem = None
        if self._bin:
            elem = self._bin.get_by_name(name)
        if not elem and self.core_pipeline:
            elem = self.core_pipeline.get_by_name(name)
        return elem

    def _update_audio_filter_params(self, new_filters: list[AudioFilterDTO]):
        """Update audio filter chain at runtime.

        Parameter-only changes: set_property on existing elements.
        Structural changes: dynamically replace filter elements via pad blocking.
        """
        uid = self.data.uid
        old_filters = self.data.audio_filters or []
        logger.log(f"[FILTER] {uid}: old={[(f.type, f.enabled) for f in old_filters]} new={[(f.type, f.enabled, f.params) for f in new_filters]}", level='DEBUG')

        # Check if filter structure matches (same count, types, and enabled state)
        structure_match = (
            len(new_filters) == len(old_filters) and
            all(n.type == o.type and n.enabled == o.enabled
                for n, o in zip(new_filters, old_filters))
        )

        if structure_match:
            def do_update_params():
                update_filter_params(new_filters, self._find_element, uid)
                return False
            GLib.idle_add(do_update_params)
        else:
            GLib.idle_add(self._rebuild_filter_chain, new_filters)

        self.data.audio_filters = new_filters

    def _rebuild_filter_chain(self, new_filters):
        """Replace audio filter elements between identity anchors."""
        uid = self.data.uid
        logger.log(f"[FILTER] {uid}: rebuild {[(f.type, f.enabled) for f in new_filters]}", level='DEBUG')
        af_in = self._find_element(f"af_in_{uid}")
        af_out = self._find_element(f"af_out_{uid}")

        if not af_in or not af_out:
            logger.log(f"[FILTER] {uid}: af_in={'found' if af_in else 'MISSING'} af_out={'found' if af_out else 'MISSING'}", level='ERROR')
            return False

        pipe = af_in.get_parent()
        return rebuild_between_anchors(af_in, af_out, new_filters, uid, pipe)

    def _update_video_filter_params(self, new_filters: list[VideoFilterDTO]):
        """Update video filter chain at runtime — mirrors audio filter logic."""
        uid = self.data.uid
        old_filters = self.data.video_filters or []

        structure_match = (
            len(new_filters) == len(old_filters) and
            all(n.type == o.type and n.enabled == o.enabled
                for n, o in zip(new_filters, old_filters))
        )

        if structure_match:
            def do_update_params():
                update_filter_params(new_filters, self._find_element, uid,
                                     anchor_in=f"vf_in_{uid}", anchor_out=f"vf_out_{uid}")
                return False
            GLib.idle_add(do_update_params)
        else:
            GLib.idle_add(self._rebuild_video_filter_chain, new_filters)

        self.data.video_filters = new_filters

    def _rebuild_video_filter_chain(self, new_filters):
        """Replace video filter elements between vf_in/vf_out anchors."""
        uid = self.data.uid
        logger.log(f"Video filter rebuild {uid}: {[(f.type, f.enabled) for f in new_filters]}", level='DEBUG')
        vf_in = self._find_element(f"vf_in_{uid}")
        vf_out = self._find_element(f"vf_out_{uid}")

        if not vf_in or not vf_out:
            logger.log(f"Video filter anchors missing for {uid}", level='ERROR')
            return False

        pipe = vf_in.get_parent()
        return rebuild_between_anchors(vf_in, vf_out, new_filters, uid, pipe,
                                        element_map=VIDEO_FILTER_ELEMENT_MAP, audio=False)

    async def update(self, data):
        if not isinstance(data, updateInputDTO):
            data = updateInputDTO.parse_obj(data)
        if data.loop is not None:
            self.data.loop = data.loop
        if data.volume is not None:
            self.data.volume = data.volume
            if self.volume_element:
                self.volume_element.set_property('volume', data.volume)
        if data.audio_filters is not None:
            self._update_audio_filter_params(data.audio_filters)
        if data.video_filters is not None:
            self._update_video_filter_params(data.video_filters)
        if data.fit is not None:
            self.set_fit(data.fit)
        if data.state is not None and data.state in ('PLAYING', 'PAUSED'):
            gst_state = Gst.State.PLAYING if data.state == 'PLAYING' else Gst.State.PAUSED
            if self._bin:
                was_paused = self.data.state == 'PAUSED'
                def do_set_state(target_state=gst_state, resuming=was_paused and gst_state == Gst.State.PLAYING):
                    try:
                        if target_state == Gst.State.PLAYING:
                            self._bin.set_locked_state(False)
                            self._bin.sync_state_with_parent()
                            if resuming:
                                # Flush seek via send_event to reset timestamps
                                # after pause — prevents fast-forward from buffered data
                                pipeline = self.get_pipeline()
                                if pipeline:
                                    pos_ok, pos = pipeline.query_position(Gst.Format.TIME)
                                    if pos_ok and pos >= 0:
                                        seek_event = Gst.Event.new_seek(
                                            1.0, Gst.Format.TIME,
                                            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                                            Gst.SeekType.SET, pos,
                                            Gst.SeekType.NONE, 0)
                                        pipeline.send_event(seek_event)
                        else:
                            self._bin.set_locked_state(True)
                            self._bin.set_state(target_state)
                    except Exception as e:
                        logger.log(f"set_state failed for {self.data.uid}: {e}", level='ERROR')
                    return False
                GLib.idle_add(do_set_state)
                self.data.state = data.state
        if data.position is not None:
            self.seek_to_position(data.position)
            self.data.position = data.position

        safe_broadcast("UPDATE", self.data)

    def set_fit(self, fit: bool):
        """Toggle add-borders on videoscale at runtime."""
        self.data.fit = fit
        uid = self.data.uid
        # Try both naming conventions (bin-based and string-based inputs)
        for name in [f"videoscale_{uid}", f"videoscale_out_{uid}"]:
            elem = None
            if self._bin:
                elem = self._bin.get_by_name(name)
            if not elem and self.core_pipeline:
                elem = self.core_pipeline.get_by_name(name)
            if elem:
                elem.set_property("add-borders", fit)

    def get_pipeline(self):
        """Return queryable element for position/duration.
        For simple inputs (testsrc), return the bin. Subclasses like uridecodebin3 override."""
        return self._bin
