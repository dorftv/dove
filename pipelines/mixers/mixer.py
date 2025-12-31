from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from logger import logger
from api.mixers_dtos import mixerCutDTO, mixerSlotDTO, mixerInputsDTO, mixerInputDTO, mixerDTO
from api.input_models import AudioFilterDTO, VideoFilterDTO
from pipelines.base import GSTBase
from pipelines.audio_filters import (
    FILTER_ELEMENT_MAP, update_filter_params, rebuild_between_anchors,
    create_filter_elements, link_filter_chain, transform_filter_param,
)
from pipelines.video_filters import VIDEO_FILTER_ELEMENT_MAP
import gi
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GLib, GstVideo
from event_loop_bridge import safe_broadcast


class Mixer(GSTBase, ABC):
    data: mixerDTO
    video_mixer: Optional[Gst.Element] = None
    audio_mixer: Optional[Gst.Element] = None
    core_pipeline: Optional[Gst.Pipeline] = None
    _bin: Optional[Gst.Bin] = None  # For dynamic addition
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._slot_queues = {}
        self._tee_pads = {}
        self._ghost_pads = {}
        self._drop_probes = {}
        self._slot_filters = {}
        self._ghost_pad_counter = 0
    _ghost_pad_counter: int = 0  # Counter for unique ghost pad names

    # CHANGED: Output to tee instead of interpipesink
    def get_video_end(self) -> str:
        return f" queue max-size-time=300000000 leaky=downstream max-size-buffers=5 ! tee name=scene_video_tee_{self.data.uid} allow-not-linked=true "

    def get_audio_end(self):
        return f" queue max-size-time=300000000 leaky=downstream max-size-buffers=5 ! tee name=scene_audio_tee_{self.data.uid} allow-not-linked=true "

    # For single-pipeline architecture
    @abstractmethod
    def build_pipeline_str(self) -> str:
        """Return pipeline string fragment for this mixer. Override in subclasses."""
        pass

    def attach(self, pipeline: Gst.Pipeline):
        """Get element references after pipeline is created."""
        self.core_pipeline = pipeline
        self._bin = None  # Clear stale bin reference after rebuild
        uid = self.data.uid
        self.video_mixer = pipeline.get_by_name(f"videomixer_{uid}")
        self.audio_mixer = pipeline.get_by_name(f"audiomixer_{uid}")
        logger.log(f"Mixer {uid} attach: video_mixer={self.video_mixer}, audio_mixer={self.audio_mixer}", level='DEBUG')
        # Initialize empty tracking dicts
        self._slot_queues = {}
        self._tee_pads = {}
        self._ghost_pads = {}
        self._drop_probes = {}
        self._slot_filters = {}
        self._ghost_pad_counter = 0

    def getMixer(self, audio_or_video):
        if audio_or_video == "video":
            return self.video_mixer
        return self.audio_mixer

    def _find_element(self, name):
        """Find a named element in bin or core pipeline."""
        elem = None
        if self._bin:
            elem = self._bin.get_by_name(name)
        if not elem and self.core_pipeline:
            elem = self.core_pipeline.get_by_name(name)
        return elem

    def _update_mixer_audio_filter_params(self, new_filters: list[AudioFilterDTO]):
        """Update mixer-level audio filter chain at runtime."""
        uid = self.data.uid
        old_filters = self.data.audio_filters or []

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
            GLib.idle_add(self._rebuild_mixer_filter_chain, new_filters)

        self.data.audio_filters = new_filters

    def _rebuild_mixer_filter_chain(self, new_filters):
        """Replace mixer-level audio filter elements between identity anchors."""
        uid = self.data.uid
        af_in = self._find_element(f"af_in_{uid}")
        af_out = self._find_element(f"af_out_{uid}")

        if not af_in or not af_out:
            logger.log(f"No mixer filter anchors for {uid} — cannot rebuild", level='WARNING')
            return False

        pipe = af_in.get_parent()
        return rebuild_between_anchors(af_in, af_out, new_filters, uid, pipe)

    def _update_mixer_video_filter_params(self, new_filters: list[VideoFilterDTO]):
        """Update mixer-level video filter chain at runtime."""
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
            GLib.idle_add(self._rebuild_mixer_video_filter_chain, new_filters)

        self.data.video_filters = new_filters

    def _rebuild_mixer_video_filter_chain(self, new_filters):
        """Replace mixer-level video filter elements between vf_in/vf_out anchors."""
        uid = self.data.uid
        vf_in = self._find_element(f"vf_in_{uid}")
        vf_out = self._find_element(f"vf_out_{uid}")

        if not vf_in or not vf_out:
            logger.log(f"No mixer video filter anchors for {uid}", level='WARNING')
            return False

        pipe = vf_in.get_parent()
        return rebuild_between_anchors(vf_in, vf_out, new_filters, uid, pipe,
                                        element_map=VIDEO_FILTER_ELEMENT_MAP, audio=False)

    def _create_slot_filter_elements(self, index, enabled_filters, av='audio'):
        """Create per-slot filter elements and add them to the pipeline.

        Returns (pre, caps, filters_list, post) or None on failure.
        av: 'audio' or 'video'
        """
        # Clean up any existing slot filters first (idempotent)
        self._cleanup_slot_filter_elements(index, av)
        uid = self.data.uid
        is_audio = av == 'audio'
        prefix = f"af_slot_{index}" if is_audio else f"vf_slot_{index}"
        emap = FILTER_ELEMENT_MAP if is_audio else VIDEO_FILTER_ELEMENT_MAP
        result = create_filter_elements(uid, prefix, enabled_filters, self.core_pipeline, emap, audio=is_audio)
        if not result:
            return None

        pre, caps, filters_list, post = result

        if index not in self._slot_filters:
            self._slot_filters[index] = {}
        self._slot_filters[index][av] = {
            'pre': pre,
            'caps': caps,
            'post': post,
            'filters': filters_list,
        }

        return pre, caps, filters_list, post

    def _cleanup_slot_filter_elements(self, index, av='audio'):
        """Remove and NULL all per-slot filter elements for a given index and stream type."""
        filter_info = self._slot_filters.get(index, {}).get(av)
        if not filter_info:
            return

        pipeline_ref = self.core_pipeline
        all_elems = []
        for key in ['pre', 'caps', 'post']:
            elem = filter_info.get(key)
            if elem:
                all_elems.append(elem)
        all_elems.extend(filter_info.get('filters', []))

        # Unlink all filter elements
        for elem in all_elems:
            for pad in elem.pads:
                peer = pad.get_peer()
                if peer:
                    if pad.get_direction() == Gst.PadDirection.SRC:
                        pad.unlink(peer)
                    else:
                        peer.unlink(pad)

        def _deferred_null_filters():
            try:
                for elem in all_elems:
                    elem.set_state(Gst.State.NULL)
                    if pipeline_ref and elem.get_parent() == pipeline_ref:
                        pipeline_ref.remove(elem)
            except Exception as e:
                logger.log(f"Exception in _deferred_null_filters: {e}", level='ERROR')
            return False
        GLib.idle_add(_deferred_null_filters)

        if index in self._slot_filters:
            self._slot_filters[index].pop(av, None)

    def _update_slot_audio_filters(self, index, new_filters):
        self._update_slot_filters(index, new_filters, av='audio')

    def _update_slot_video_filters(self, index, new_filters):
        self._update_slot_filters(index, new_filters, av='video')

    def _update_slot_filters(self, index, new_filters, av='audio'):
        """Update per-slot filters at runtime (audio or video).

        Parameter-only changes: set_property on existing elements.
        Structural changes: pad block on queue src, remove old, insert new, unblock.
        """
        uid = self.data.uid
        mixerInput = self.data.getMixerInputDTO(index)
        if not mixerInput:
            return

        old_filters = getattr(mixerInput, f'{av}_filters', None) or []
        enabled_new = [f for f in new_filters if f.enabled]
        enabled_old = [f for f in old_filters if f.enabled]

        structure_match = (
            len(enabled_new) == len(enabled_old) and
            all(n.type == o.type for n, o in zip(enabled_new, enabled_old))
        )

        if structure_match and enabled_new:
            filter_info = self._slot_filters.get(index, {}).get(av)
            if filter_info:
                existing_elems = filter_info.get('filters', [])
                for i, f in enumerate(enabled_new):
                    if i < len(existing_elems):
                        for key, val in f.params.items():
                            result = transform_filter_param(f.type, key, val)
                            if result is None:
                                continue
                            key, val = result
                            try:
                                existing_elems[i].set_property(key, val)
                            except Exception as e:
                                logger.log(f"Failed to set {key}={val} on slot {index} {av} filter {i}: {e}", level='WARNING')
        else:
            self._rebuild_slot_filter_chain(index, new_filters, av=av)

        setattr(mixerInput, f'{av}_filters', new_filters)

    def _rebuild_slot_filter_chain(self, index, new_filters, av='audio'):
        """Replace per-slot filter elements in the running pipeline.

        Uses pad blocking on queue src pad to safely swap filter elements.
        av: 'audio' or 'video'
        """
        uid = self.data.uid
        queue = self._slot_queues.get(index, {}).get(av)
        if not queue:
            logger.log(f"No {av} queue for slot {index} — cannot rebuild slot filters", level='WARNING')
            return

        is_audio = av == 'audio'
        enabled_new = [f for f in new_filters if f.enabled]
        has_existing = index in self._slot_filters and av in self._slot_filters.get(index, {})

        queue_src = queue.get_static_pad("src")
        if not queue_src:
            return

        def _do_rebuild(pad, info, user_data):
            try:
                logger.log(f"Slot {index} filter rebuild: existing={has_existing}, new={len(enabled_new)}", level='DEBUG')
                # Find what's currently after queue src
                queue_src_peer = queue_src.get_peer()

                # Determine the final target pad (mixer sink pad or ghost pad)
                # Walk through existing filter chain to find it
                if has_existing:
                    filter_info = self._slot_filters[index][av]
                    af_post = filter_info['post']
                    post_src = af_post.get_static_pad("src")
                    target_pad = post_src.get_peer() if post_src else None

                    # Unlink queue from filter chain
                    if queue_src_peer:
                        queue_src.unlink(queue_src_peer)

                    # Unlink post from target
                    if target_pad and post_src:
                        post_src.unlink(target_pad)

                    # Remove all old filter elements
                    all_old = []
                    for key in ['pre', 'caps', 'post']:
                        elem = filter_info.get(key)
                        if elem:
                            all_old.append(elem)
                    all_old.extend(filter_info.get('filters', []))

                    for elem in all_old:
                        for p in elem.pads:
                            peer = p.get_peer()
                            if peer:
                                if p.get_direction() == Gst.PadDirection.SRC:
                                    p.unlink(peer)
                                else:
                                    peer.unlink(p)

                    # Defer NULL+remove to after probe (avoids EOS during pad probe)
                    pipeline_ref = self.core_pipeline
                    def _deferred_cleanup(elems=all_old):
                        for elem in elems:
                            elem.set_state(Gst.State.NULL)
                            if pipeline_ref and elem.get_parent() == pipeline_ref:
                                pipeline_ref.remove(elem)
                        return False
                    GLib.idle_add(_deferred_cleanup)

                    self._slot_filters[index].pop(av, None)
                else:
                    # No existing filters — queue src is linked directly to mixer
                    target_pad = queue_src_peer
                    if target_pad:
                        queue_src.unlink(target_pad)

                if not target_pad:
                    logger.log(f"[SLOT-FILTER] slot {index}: No target pad found!", level='ERROR')
                    return Gst.PadProbeReturn.REMOVE

                logger.log(f"Slot {index} filter target: {target_pad.get_name() if target_pad else 'None'}", level='DEBUG')

                # Create new filter chain if there are enabled filters
                if enabled_new:
                    filter_elems = self._create_slot_filter_elements(index, enabled_new, av=av)
                    if filter_elems:
                        af_pre, af_caps, filters_list, af_post = filter_elems
                        queue_src.link(af_pre.get_static_pad("sink"))
                        link_filter_chain(af_pre, af_caps, filters_list, af_post)
                        af_post.get_static_pad("src").link(target_pad)
                    else:
                        # Fallback: direct link
                        queue_src.link(target_pad)
                else:
                    # No filters — direct link queue → mixer
                    link_ok = queue_src.link(target_pad)
                    logger.log(f"Slot {index} filter cleared: link={link_ok}", level='DEBUG')

                logger.log(f"Slot {index} filter rebuild done: {len(enabled_new)} filters", level='INFO')

            except Exception as e:
                logger.log(f"Slot filter rebuild error for index {index}: {e}", level='ERROR')
                import traceback
                traceback.print_exc()

            return Gst.PadProbeReturn.REMOVE

        queue_src.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, _do_rebuild, None)

    def add_slot(self, mixerSource: mixerInputDTO = None):
        """Add a new slot (dynamically request mixer pad)."""
        if mixerSource is None:
            mixerSource = mixerInputDTO()

        index = len(self.data.sources)
        mixerSource.index = index

        for av in ["video", "audio"]:
            mixer = self.getMixer(av)
            if mixer is None:
                continue
            pad = mixer.request_pad_simple("sink_%u")
            if pad is None:
                continue

            # Initialize pad properties
            if av == "video":
                pad.set_property("alpha", 0)
                pad.set_property("width", self.data.width)
                pad.set_property("height", self.data.height)
            else:
                pad.set_property("volume", 0)
                pad.set_property("mute", True)

            mixerSource.sink = pad.get_name()

        self.data.sources.append(mixerSource)
        self.data.update_source_with_defaults(index)
        safe_broadcast("UPDATE", self.data)
        return mixerSource

    def remove_slot(self, mixerSource: mixerInputDTO = None):
        """Remove a slot (release mixer pad)."""
        if mixerSource is None:
            return

        # Unlink first
        if mixerSource.index is not None:
            self.unlink_source(mixerSource.index)

        # Release pads
        for av in ["video", "audio"]:
            mixer = self.getMixer(av)
            if mixer and mixerSource.sink:
                pad = mixer.get_static_pad(mixerSource.sink)
                if pad:
                    mixer.release_request_pad(pad)

        self.data.remove_slot(mixerSource)
        safe_broadcast("UPDATE", self.data)

    def link_source(self, index: int, source_uid: UUID):
        """Link an input or mixer's tee to a mixer slot."""
        from pipeline_handler import HandlerSingleton

        mixerInput = self.data.getMixerInputDTO(index)
        if not mixerInput:
            logger.log(f"Mixer slot {index} not found", level='ERROR')
            return

        # Mute mixer pads before cleanup (no DROP probes — those corrupt pipeline under rapid re-linking)
        if mixerInput.src and mixerInput.src != "None":
            for av in ["video", "audio"]:
                mixer = self.getMixer(av)
                if mixer and mixerInput.sink:
                    pad = mixer.get_static_pad(mixerInput.sink)
                    if pad:
                        if av == "video":
                            pad.set_property("alpha", 0)
                        else:
                            pad.set_property("volume", 0)
                            pad.set_property("mute", True)

        # Always hard-cleanup old queues/ghost pads before creating new ones.
        # Previous soft-unlink may have left connections in place.
        for av in ["video", "audio"]:
            self._cleanup_slot_connections(index, av)
            mixer = self.getMixer(av)
            if mixer and mixerInput.sink:
                sink_pad = mixer.get_static_pad(mixerInput.sink)
                if sink_pad:
                    sink_pad.send_event(Gst.Event.new_flush_start())
                    sink_pad.send_event(Gst.Event.new_flush_stop(True))

        # Get source component - could be input or mixer
        handler = HandlerSingleton()
        input_component = handler.get_pipeline("inputs", source_uid)
        mixer_component = handler.get_pipeline("mixers", source_uid) if not input_component else None

        for av in ["video", "audio"]:
            # Skip if source input has this stream disabled
            if input_component:
                if av == "video" and not getattr(input_component.data, 'has_video', True):
                    continue
                if av == "audio" and not getattr(input_component.data, 'has_audio', True):
                    continue

            # Get source's tee - prefer stored reference, fallback to pipeline search
            source_tee = None
            source_bin = None

            if input_component:
                # Source is an input
                source_tee = input_component.video_tee if av == "video" else input_component.audio_tee
                source_bin = getattr(input_component, '_bin', None)
                tee_name = f"{av}_tee_{source_uid}"
                logger.log(f"link_source {av}: component={type(input_component).__name__}, tee={source_tee}, bin={source_bin}", level='DEBUG')
            elif mixer_component:
                # Source is a mixer/scene - use scene_video_tee / scene_audio_tee naming
                source_bin = getattr(mixer_component, '_bin', None)
                tee_name = f"scene_{av}_tee_{source_uid}"
                # Try to get from bin first
                if source_bin:
                    source_tee = source_bin.get_by_name(tee_name)
            else:
                tee_name = f"{av}_tee_{source_uid}"

            if not source_tee:
                source_tee = self.core_pipeline.get_by_name(tee_name)

            if not source_tee:
                logger.log(f"Source tee not found: {tee_name}", level='ERROR')
                continue

            # Get mixer sink pad
            mixer = self.getMixer(av)
            if not mixer:
                logger.log(f"link_source: {av} mixer is None for {self.data.uid}!", level='ERROR')
                continue
            sink_pad = mixer.get_static_pad(mixerInput.sink)
            if not sink_pad:
                # List all pads on the mixer for debugging
                pads = [p.get_name() for p in mixer.pads]
                logger.log(f"link_source: {av} available pads: {pads}", level='ERROR')
                logger.log(f"Mixer pad not found: {mixerInput.sink}", level='ERROR')
                continue

            # Create queue and add to main pipeline (use counter for unique name)
            self._ghost_pad_counter += 1
            queue_name = f"queue_{av}_{self.data.uid}_{index}_{self._ghost_pad_counter}"
            queue = Gst.ElementFactory.make("queue", queue_name)
            queue.set_property("leaky", 2)  # downstream: drop old buffers when full
            queue.set_property("max-size-time", 500000000)  # 500ms
            queue.set_property("max-size-buffers", 5)
            queue.set_property("max-size-bytes", 0)
            self.core_pipeline.add(queue)
            queue.sync_state_with_parent()

            # Store for later cleanup
            if index not in self._slot_queues:
                self._slot_queues[index] = {}
            self._slot_queues[index][av] = queue

            # Request tee src pad
            tee_pad = source_tee.request_pad_simple("src_%u")
            if index not in self._tee_pads:
                self._tee_pads[index] = {}
            self._tee_pads[index][av] = tee_pad

            queue_sink = queue.get_static_pad("sink")
            final_src_pad = queue.get_static_pad("src")

            # Insert per-slot audio filter chain: queue → af_pre → caps(F32LE) → [filters] → af_post → mixer
            if av == "audio":
                slot_audio_filters = getattr(mixerInput, 'audio_filters', None) or []
                enabled_filters = [f for f in slot_audio_filters if f.enabled]
                if enabled_filters:
                    uid = self.data.uid
                    filter_elems = self._create_slot_filter_elements(index, enabled_filters)
                    if filter_elems:
                        af_pre, af_caps, filters_list, af_post = filter_elems
                        queue.get_static_pad("src").link(af_pre.get_static_pad("sink"))
                        link_filter_chain(af_pre, af_caps, filters_list, af_post)
                        final_src_pad = af_post.get_static_pad("src")

            # Eat EOS events so they never reach the mixer.
            # Without this, one input's EOS stalls the compositor/audiomixer,
            # freezing all other inputs feeding the same mixer.
            def eos_event_probe(pad, info, user_data):
                event = info.get_event()
                if event.type == Gst.EventType.EOS:
                    return Gst.PadProbeReturn.DROP
                return Gst.PadProbeReturn.OK
            eos_probe_id = final_src_pad.add_probe(Gst.PadProbeType.EVENT_DOWNSTREAM, eos_event_probe, None)

            # Initialize ghost pad tracking for this slot
            if index not in self._ghost_pads:
                self._ghost_pads[index] = {}
            if av not in self._ghost_pads[index]:
                self._ghost_pads[index][av] = {}
            self._ghost_pads[index][av]['eos_probe'] = (final_src_pad, eos_probe_id)

            # Link tee → queue (handle bin boundary if source is in bin)
            if source_bin:
                # Create ghost pad on source bin to expose tee src
                # Use counter for unique names since we don't remove ghost pads from input bins
                self._ghost_pad_counter += 1
                ghost_name = f"mixer_{self.data.uid}_{av}_out_{index}_{self._ghost_pad_counter}"
                source_ghost = Gst.GhostPad.new(ghost_name, tee_pad)
                source_ghost.set_active(True)
                source_bin.add_pad(source_ghost)
                self._ghost_pads[index][av]['input'] = (source_bin, source_ghost)
                link_result_tee = source_ghost.link(queue_sink)
            else:
                link_result_tee = tee_pad.link(queue_sink)

            # Link final element → mixer (handle bin boundary if mixer is in bin)
            if self._bin:
                # Create ghost pad on mixer bin to expose mixer sink
                self._ghost_pad_counter += 1
                ghost_name = f"mixer_{self.data.uid}_{av}_in_{index}_{self._ghost_pad_counter}"
                mixer_ghost = Gst.GhostPad.new(ghost_name, sink_pad)
                mixer_ghost.set_active(True)
                self._bin.add_pad(mixer_ghost)
                self._ghost_pads[index][av]['mixer'] = (self._bin, mixer_ghost)
                link_result_mixer = final_src_pad.link(mixer_ghost)
            else:
                link_result_mixer = final_src_pad.link(sink_pad)

            logger.log(f"Link results for slot {index} {av}: tee→queue={link_result_tee}, queue→mixer={link_result_mixer}", level='DEBUG')

            # Make visible/audible
            if av == "video":
                sink_pad.set_property("alpha", 1.0)
                logger.log(f"Set video alpha=1.0 on {sink_pad.get_name()}", level='DEBUG')
            else:
                # For audio, send flush events to reset the pad state before enabling
                sink_pad.send_event(Gst.Event.new_flush_start())
                sink_pad.send_event(Gst.Event.new_flush_stop(True))
                sink_pad.set_property("volume", 1.0)
                sink_pad.set_property("mute", False)

            logger.log(f"Linked {tee_name} to mixer slot {index}", level='DEBUG')

        # Update DTO src BEFORE applying pad properties (fit path needs src)
        self.data.update_mixer_input(index, src=str(source_uid))

        # Apply pad properties from DTO
        for av in ["video", "audio"]:
            self.update_pad_from_sources(av, index)

        # Force keyframe on scene's preview encoder so it updates immediately
        self._force_preview_keyframe()

        safe_broadcast("UPDATE", self.data)

    def _cleanup_slot_connections(self, index, av):
        """Hard cleanup of old queue/ghost pads for a slot. Only called from
        link_source() when re-linking (brief glitch acceptable during source switch)."""
        # Remove DROP probe before queue cleanup
        drop_info = self._drop_probes.get(index, {}).get(av)
        if drop_info:
            pad, probe_id = drop_info
            if pad:
                pad.remove_probe(probe_id)
            if index in self._drop_probes and av in self._drop_probes[index]:
                del self._drop_probes[index][av]

        # Clean up per-slot filter elements before queue removal
        self._cleanup_slot_filter_elements(index, av)

        if index in self._slot_queues and av in self._slot_queues[index]:
            old_queue = self._slot_queues[index][av]
            old_src = old_queue.get_static_pad("src")
            if old_src:
                peer = old_src.get_peer()
                if peer:
                    old_src.unlink(peer)
            old_sink = old_queue.get_static_pad("sink")
            if old_sink:
                peer = old_sink.get_peer()
                if peer:
                    peer.unlink(old_sink)
            old_queue.set_locked_state(True)
            pipeline_ref = self.core_pipeline
            def _deferred_null_queue():
                try:
                    old_queue.set_state(Gst.State.NULL)
                    if pipeline_ref and old_queue.get_parent() == pipeline_ref:
                        pipeline_ref.remove(old_queue)
                except Exception as e:
                    logger.log(f"Exception in _deferred_null_queue: {e}", level='ERROR')
                return False
            GLib.idle_add(_deferred_null_queue)
            del self._slot_queues[index][av]

        if index in self._ghost_pads and av in self._ghost_pads[index]:
            ghost_info = self._ghost_pads[index].get(av, {})
            # Remove EOS probe before cleaning up the queue
            eos_info = ghost_info.get('eos_probe')
            if eos_info:
                pad, probe_id = eos_info
                if pad:
                    pad.remove_probe(probe_id)
            # Clean up mixer-side ghost pad
            if 'mixer' in ghost_info:
                bin_elem, ghost_pad = ghost_info['mixer']
                if bin_elem and ghost_pad:
                    ghost_pad.set_active(False)
                    ghost_pad.set_target(None)
                    bin_elem.remove_pad(ghost_pad)
            # Clean up input/source-side ghost pad
            if 'input' in ghost_info:
                bin_elem, ghost_pad = ghost_info['input']
                if bin_elem and ghost_pad:
                    ghost_pad.set_active(False)
                    ghost_pad.set_target(None)
                    bin_elem.remove_pad(ghost_pad)
            if av in self._ghost_pads[index]:
                del self._ghost_pads[index][av]

        # Release old tee pad to avoid leaking requested pads
        if index in self._tee_pads and av in self._tee_pads[index]:
            old_tee_pad = self._tee_pads[index][av]
            tee = old_tee_pad.get_parent()
            if tee:
                tee.release_request_pad(old_tee_pad)
            del self._tee_pads[index][av]

    def unlink_source(self, index: int):
        """Soft-unlink: mute mixer pads and isolate queues with DROP probes.

        No pad unlinking — that causes the mixer to stall all pads.
        Instead, DROP probes on queue src pads prevent ANY data/events
        (including FLUSH from ghost pad deactivation) from reaching the mixer.
        The mixer's ignore-inactive-pads handles the quiet pads.
        Hard cleanup (actual pad unlinks) only happens in link_source() when
        re-linking, where a brief glitch is acceptable.
        """
        mixerInput = self.data.getMixerInputDTO(index)
        if not mixerInput or mixerInput.src == "None":
            return

        for av in ["video", "audio"]:
            mixer = self.getMixer(av)
            if mixer and mixerInput.sink:
                sink_pad = mixer.get_static_pad(mixerInput.sink)
                if sink_pad:
                    if av == "video":
                        sink_pad.set_property("alpha", 0)
                    else:
                        sink_pad.set_property("volume", 0)
                        sink_pad.set_property("mute", True)

            # Isolate the mixer: add DROP probe on queue src pad.
            # This catches buffers, downstream events, AND flush events
            # (flush events need EVENT_FLUSH — they bypass EVENT_DOWNSTREAM).
            # When the input bin later goes NULL, its ghost pads deactivate
            # causing FLUSH_START to propagate — the probe eats it.
            queue = self._slot_queues.get(index, {}).get(av)
            if queue:
                queue_src = queue.get_static_pad("src")
                if queue_src:
                    # Remove previous DROP probe if any
                    old_drop = self._drop_probes.get(index, {}).get(av)
                    if old_drop:
                        old_pad, old_id = old_drop
                        if old_pad:
                            old_pad.remove_probe(old_id)
                    probe_id = queue_src.add_probe(
                        Gst.PadProbeType.BUFFER | Gst.PadProbeType.BUFFER_LIST |
                        Gst.PadProbeType.EVENT_DOWNSTREAM | Gst.PadProbeType.EVENT_FLUSH,
                        lambda p, i, d: Gst.PadProbeReturn.DROP, None)
                    if index not in self._drop_probes:
                        self._drop_probes[index] = {}
                    self._drop_probes[index][av] = (queue_src, probe_id)
                queue.set_locked_state(True)
                logger.log(f"Isolated queue src for slot {index} {av}", level='DEBUG')

        self.data.update_mixer_input(index, src="None")
        safe_broadcast("UPDATE", self.data)
        logger.log(f"Soft-unlinked source from mixer slot {index}", level='DEBUG')

    def _compute_slot_fit(self, source_uid, slot_w, slot_h):
        """Compute pad width/height/xpos/ypos to fit source within slot dimensions.

        For uridecodebin3 inputs the scene compositor receives native resolution directly,
        so setting the pad to (display_w, display_h) scales correctly.
        For playlist inputs the frame is at global resolution (stretched) —
        the compositor pad size undoes the stretching via the same math.
        """
        from pipeline_handler import HandlerSingleton
        from uuid import UUID as _UUID
        handler = HandlerSingleton()
        try:
            uid = _UUID(str(source_uid))
        except (ValueError, TypeError):
            return slot_w, slot_h, 0, 0
        input_component = handler.get_pipeline("inputs", uid)
        if not input_component:
            return slot_w, slot_h, 0, 0

        native_w = getattr(input_component.data, 'width', None)
        native_h = getattr(input_component.data, 'height', None)

        logger.log(f"_compute_slot_fit: src={source_uid} native={native_w}x{native_h} slot={slot_w}x{slot_h}", level='DEBUG')

        if not native_w or not native_h or native_w <= 0 or native_h <= 0:
            return slot_w, slot_h, 0, 0

        source_ratio = native_w / native_h
        slot_ratio = slot_w / slot_h

        if abs(source_ratio - slot_ratio) < 0.01:
            # Same aspect ratio — fill the slot
            return slot_w, slot_h, 0, 0

        if source_ratio > slot_ratio:
            # Source is wider — fit to width
            display_w = slot_w
            display_h = int(slot_w / source_ratio) & ~1
        else:
            # Source is taller — fit to height
            display_h = slot_h
            display_w = int(slot_h * source_ratio) & ~1

        xpos = (slot_w - display_w) // 2
        ypos = (slot_h - display_h) // 2

        return display_w, display_h, xpos, ypos

    def mute_source(self, source_uid):
        """Mute all mixer pads referencing a given input UID (alpha=0, volume=0).

        Called when an input errors out to prevent glitches in program output.
        """
        for source in self.data.sources:
            if str(source.src) != str(source_uid):
                continue
            if not source.sink:
                continue
            for av in ["video", "audio"]:
                mixer = self.getMixer(av)
                if not mixer:
                    continue
                pad = mixer.get_static_pad(source.sink)
                if not pad:
                    continue
                if av == "video":
                    pad.set_property("alpha", 0)
                else:
                    pad.set_property("volume", 0)
                    pad.set_property("mute", True)
            logger.log(f"Auto-muted slot {source.index} (source {str(source_uid)[:8]} errored)", level='INFO')

    def update_pad_from_sources(self, audio_or_video, index):
        """Update pad properties from DTO. Handles sizing="fit" via _compute_slot_fit."""
        mixerInput = self.data.getMixerInputDTO(index)
        if not mixerInput:
            return

        mixer = self.getMixer(audio_or_video)
        if not mixer or not mixerInput.sink:
            return

        sink_pad = mixer.get_static_pad(mixerInput.sink)
        if not sink_pad:
            return

        if audio_or_video == "video":
            sizing = getattr(mixerInput, 'sizing', 'stretch')

            # Set position and dimensions from DTO
            for prop in ['xpos', 'ypos', 'width', 'height']:
                val = getattr(mixerInput, prop, None)
                if val is not None:
                    sink_pad.set_property(prop, val)

            # 0 = none (stretch to fill), 1 = keep-aspect-ratio (fit with padding)
            policy = 1 if sizing == 'fit' else 0
            sink_pad.set_property("sizing-policy", policy)

            for prop in ['alpha', 'zorder']:
                val = getattr(mixerInput, prop, None)
                if val is not None:
                    sink_pad.set_property(prop, val)
        else:
            for prop in ['volume', 'mute']:
                val = getattr(mixerInput, prop, None)
                if val is not None:
                    sink_pad.set_property(prop, val)

    def _force_preview_keyframe(self):
        """Force keyframe on this scene's preview video encoder."""
        from pipeline_handler import HandlerSingleton
        handler = HandlerSingleton()
        for enc in handler._pipelines.get('encoders', []):
            if (getattr(enc.data, 'is_preview', False) and
                    str(enc.data.src) == str(self.data.uid) and
                    enc.data.type == "video" and enc.tee):
                event = GstVideo.video_event_new_upstream_force_key_unit(
                    Gst.CLOCK_TIME_NONE, True, 0)
                if enc._bin:
                    src_pad = enc._bin.get_static_pad("src")
                    if src_pad:
                        src_pad.send_event(event)
                else:
                    enc.tee.send_event(event)
                break

    def add_source(self, data):
        """API wrapper: Link input to mixer slot."""
        from uuid import UUID
        from event_loop_bridge import bridge
        index = data.index
        src = data.src
        if src and str(src) != "None":
            if isinstance(src, str):
                src = UUID(src)
            # Schedule on GLib thread for GStreamer operations
            bridge.run_sync_in_glib(lambda: self.link_source(index, src))
        return self.data

    def remove_source(self, data):
        """API wrapper: Unlink source from mixer slot."""
        from event_loop_bridge import bridge
        index = data.index
        # Schedule on GLib thread for GStreamer operations
        bridge.run_sync_in_glib(lambda: self.unlink_source(index))
        return self.data

    def cleanup(self):
        """Clean up all slots — call before mixer deletion."""
        for index in list(self._ghost_pads.keys()):
            for av in list(self._ghost_pads.get(index, {}).keys()):
                try:
                    self._cleanup_slot_connections(index, av)
                except Exception:
                    pass
        self._ghost_pads.clear()
        self._slot_queues.clear()
        self._tee_pads.clear()
        self._slot_filters.clear()
