from typing import Optional
from uuid import UUID

from event_loop_bridge import safe_broadcast
from logger import logger

from pipelines.mixers.mixer import Mixer
from pipelines.audio_filters import build_audio_filter_str
from pipelines.video_filters import build_video_filter_str
from api.mixers_dtos import programMixerDTO, mixerCutProgramDTO
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib


class programMixer(Mixer):
    data: programMixerDTO
    _fallback_pattern: int = 2  # black
    _fade_timer_id: Optional[int] = None
    _flush_timer_id: Optional[int] = None
    _fade_step: int = 0
    _fade_total_steps: int = 0
    _fade_old_index: Optional[int] = None
    _fade_new_index: Optional[int] = None
    _pending_transition: Optional[dict] = None
    _transition_scheduled: bool = False

    def build_pipeline_str(self) -> str:
        """Return pipeline string with mixer elements and output tees."""
        uid = self.data.uid
        caps_video = self.get_caps('video')
        caps_audio = self.get_caps('audio')

        # Fallback source for compositor
        video_filters = getattr(self.data, 'video_filters', None) or []
        vfilter_str = build_video_filter_str(uid, video_filters)
        video_str = (
            f" videotestsrc do-timestamp=true is-live=true pattern=2 name=fallback_video_{uid} ! {caps_video} ! "
            f" compositor name=videomixer_{uid} background=black latency=70000000 start-time-selection=first force-live=true ignore-inactive-pads=true "
            f" ! videorate skip-to-first=true ! videoconvert ! videoscale ! {caps_video} "
            f" ! {vfilter_str} ! {self.get_video_end()} "
        )

        # Fallback source for audiomixer
        filters = getattr(self.data, 'audio_filters', None) or []
        filter_str = build_audio_filter_str(uid, filters)
        audio_str = (
            f" audiotestsrc do-timestamp=true is-live=true wave=4 name=fallback_audio_{uid} ! {caps_audio} ! "
            f" audiomixer name=audiomixer_{uid} latency=70000000 start-time-selection=first force-live=true ignore-inactive-pads=true "
            f" ! {filter_str}"
            f" ! level name=level_{uid} interval=200000000 post-messages=true "
            f" ! {caps_audio} ! {self.get_audio_end()} "
        )

        return video_str + audio_str

    def attach(self, pipeline: Gst.Pipeline):
        """Get element references and create initial slots."""
        super().attach(pipeline)

        # Create 2 slots for program mixer (for A/B switching)
        self.add_slot()
        self.add_slot()

        # Create additional slots for overlays if pre-configured
        n = len(self.data.sources)
        for i in range(2, n):
            self.add_slot()

        # Link any sources that were pre-configured in the DTO
        for i, source in enumerate(self.data.sources):
            if source.src and source.src != "None":
                try:
                    self.link_source(i, UUID(str(source.src)))
                    for av in ["audio", "video"]:
                        self.update_pad_from_sources(av, i)
                except Exception as e:
                    logger.log(f"Failed to link initial source at index {i}: {e}", level='ERROR')

    async def cut_program(self, data: mixerCutProgramDTO):
        """Switch program source using A/B slots (last-wins with cooldown)."""
        from event_loop_bridge import bridge

        src_uid = None
        if data.src and data.src != "None":
            try:
                src_uid = UUID(str(data.src))
            except ValueError:
                logger.log(f"cut_program: invalid UUID {data.src!r}", level='WARNING')
                return data

        # Store latest request — rapid clicks overwrite, only last one executes
        self._pending_transition = {
            'src_uid': src_uid,
            'transition': data.transition,
            'duration': data.duration or 500,
        }

        if not self._transition_scheduled:
            self._transition_scheduled = True
            bridge.run_sync_in_glib(self._process_transition)

        return data

    def cut_program_sync(self, data: mixerCutProgramDTO):
        """Synchronous cut for use on GLib thread (startup)."""
        src_uid = None
        if data.src and data.src != "None":
            try:
                src_uid = UUID(str(data.src))
            except ValueError:
                logger.log(f"cut_program_sync: invalid UUID {data.src!r}", level='WARNING')
                return
        self._pending_transition = {
            'src_uid': src_uid,
            'transition': data.transition,
            'duration': data.duration or 500,
        }
        self._transition_scheduled = True
        self._process_transition()

    def _process_transition(self):
        """Execute the latest pending transition on GLib thread."""
        pending = self._pending_transition
        if pending is None:
            self._transition_scheduled = False
            return
        self._pending_transition = None

        src_uid = pending['src_uid']
        transition = pending['transition']
        duration = pending['duration']

        # Compute indices HERE on GLib thread — always reads latest data.active
        if self.data.active is None:
            old_index = None
            index = 0
        else:
            old_index = self.data.active
            index = 0 if self.data.active == 1 else 1

        self._cancel_fade()

        # Only re-link if the source changed — skip expensive teardown+rebuild for A/B toggling
        if src_uid:
            current_src = self.data.sources[index].src if index < len(self.data.sources) else None
            if str(current_src) != str(src_uid):
                self.link_source(index, src_uid)
            else:
                # Source already linked — just make visible
                self._show_slot(index)
        self.data.active = index

        if transition == "fade":
            self._do_fade(index, old_index, duration)
        else:
            if old_index is not None:
                self._hide_slot(old_index)
            safe_broadcast("UPDATE", self.data)

        # debounce: 100ms gate before processing next queued transition
        if self._flush_timer_id is not None:
            GLib.source_remove(self._flush_timer_id)
        self._flush_timer_id = GLib.timeout_add(100, self._flush_pending_transition)

    def _flush_pending_transition(self):
        """After cooldown, process any queued transition or release the lock."""
        self._flush_timer_id = None
        if self._pending_transition is not None:
            self._process_transition()
        else:
            self._transition_scheduled = False
        return False

    def _show_slot(self, index):
        """Show a slot — alpha=1, volume=1, mute=False."""
        source = self.data.sources[index]
        for av in ["video", "audio"]:
            mixer = self.getMixer(av)
            if mixer and source.sink:
                pad = mixer.get_static_pad(source.sink)
                if pad:
                    if av == "video":
                        pad.set_property("alpha", 1.0)
                    else:
                        pad.set_property("volume", 1.0)
                        pad.set_property("mute", False)

    def _hide_slot(self, index):
        """Hide a slot — alpha=0, volume=0, mute=True. No structural changes."""
        source = self.data.sources[index]
        for av in ["video", "audio"]:
            mixer = self.getMixer(av)
            if mixer and source.sink:
                pad = mixer.get_static_pad(source.sink)
                if pad:
                    if av == "video":
                        pad.set_property("alpha", 0)
                    else:
                        pad.set_property("volume", 0)
                        pad.set_property("mute", True)

    def _cancel_fade(self):
        """Cancel any active fade, snapping to final state."""
        if self._fade_timer_id is None:
            return

        GLib.source_remove(self._fade_timer_id)
        self._fade_timer_id = None

        new_index = self._fade_new_index
        old_index = self._fade_old_index

        for av in ["video", "audio"]:
            mixer = self.getMixer(av)
            prop = "alpha" if av == "video" else "volume"

            if new_index is not None:
                new_pad = mixer.get_static_pad(self.data.sources[new_index].sink)
                if new_pad:
                    new_pad.set_property(prop, 1.0)

            if old_index is not None:
                old_pad = mixer.get_static_pad(self.data.sources[old_index].sink)
                if old_pad:
                    old_pad.set_property(prop, 0.0)

        if old_index is not None:
            self._hide_slot(old_index)

        self._fade_step = 0
        self._fade_total_steps = 0
        self._fade_old_index = None
        self._fade_new_index = None

    def _do_fade(self, new_index, old_index, duration_ms):
        """Start a crossfade animation between two slots."""
        steps = max(1, duration_ms // 25)  # ~40fps
        step_ms = duration_ms // steps

        # Override link_source's alpha=1 on new slot — start invisible
        for av in ["video", "audio"]:
            mixer = self.getMixer(av)
            new_pad = mixer.get_static_pad(self.data.sources[new_index].sink)
            if new_pad:
                if av == "video":
                    new_pad.set_property("alpha", 0.0)
                else:
                    new_pad.set_property("volume", 0.0)

        self._fade_step = 0
        self._fade_total_steps = steps
        self._fade_old_index = old_index
        self._fade_new_index = new_index

        def fade_tick():
            try:
                self._fade_step += 1
                t = self._fade_step / self._fade_total_steps

                for av in ["video", "audio"]:
                    mixer = self.getMixer(av)
                    prop = "alpha" if av == "video" else "volume"

                    new_pad = mixer.get_static_pad(self.data.sources[new_index].sink)
                    if new_pad:
                        new_pad.set_property(prop, t)

                    if old_index is not None:
                        old_pad = mixer.get_static_pad(self.data.sources[old_index].sink)
                        if old_pad:
                            old_pad.set_property(prop, 1.0 - t)

                if self._fade_step >= self._fade_total_steps:
                    if old_index is not None:
                        self._hide_slot(old_index)
                    self._fade_timer_id = None
                    self._force_preview_keyframe()
                    safe_broadcast("UPDATE", self.data)
                    return False  # Stop timer

                return True  # Continue
            except Exception as e:
                logger.log(f"Exception in fade_tick: {e}", level='ERROR')
                self._fade_timer_id = None
                return False

        self._fade_timer_id = GLib.timeout_add(step_ms, fade_tick)

    async def update(self, data):
        """Handle program mixer updates (audio/video filters, etc.)."""
        from api.input_models import AudioFilterDTO, VideoFilterDTO

        if 'audio_filters' in data:
            new_filters = [AudioFilterDTO(**f) if isinstance(f, dict) else f for f in data['audio_filters']]
            self._update_mixer_audio_filter_params(new_filters)
        if 'video_filters' in data:
            new_filters = [VideoFilterDTO(**f) if isinstance(f, dict) else f for f in data['video_filters']]
            self._update_mixer_video_filter_params(new_filters)
        if 'audio_filters' in data or 'video_filters' in data:
            safe_broadcast("UPDATE", self.data)

    def cleanup(self):
        """Cancel pending timers before mixer teardown."""
        if self._flush_timer_id is not None:
            GLib.source_remove(self._flush_timer_id)
            self._flush_timer_id = None
        self._cancel_fade()
        super().cleanup()

