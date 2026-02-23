import asyncio
import sys
import time
from pathlib import Path
from typing import List, ClassVar, Any, Optional
from uuid import UUID
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

from api.input_models import PositionDTO
from event_loop_bridge import bridge, safe_broadcast
from logger import logger
from pipelines.core_pipeline import CorePipeline


def is_subclass_str(cls, base_name):
    return base_name in [base.__name__ for base in cls.__mro__]


class PipelineHandler(object):
    _pipelines: dict[str, List["GSTBase"]] = {"inputs": {}, "outputs": {}, "mixers": {}, "encoders": {}}
    mainloop: GObject.MainLoop
    core_pipeline: CorePipeline = None
    _defer_build: bool = True  # Defer building until initial setup complete

    def __init__(self):
        Gst.init(sys.argv)

        self._pipelines["inputs"] = []
        self._pipelines["outputs"] = []
        self._pipelines["mixers"] = []
        self._pipelines["encoders"] = []
        self.core_pipeline = CorePipeline()
        self._defer_build = True
        self.mainloop = None
        self._start_time = time.monotonic()
        self._tick()

    def _tick(self):
        GLib.timeout_add_seconds(1, self._tick_callback)

    def get_uptime(self):
        """Return uptime in seconds."""
        return int(time.monotonic() - self._start_time)

    def _tick_callback(self):
        """GLib callback - queries GStreamer, then schedules async broadcast."""
        try:
            tick_data = {"uptime": self.get_uptime()}
            try:
                import os
                load1 = os.getloadavg()[0]
                cpu_count = os.cpu_count() or 1
                tick_data['load1'] = round(load1, 2)
                tick_data['load_percent'] = round(load1 / cpu_count * 100, 1)
                tick_data['fds'] = len(os.listdir('/proc/self/fd'))
                with open('/proc/self/status') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            tick_data['rss_mb'] = round(int(line.split()[1]) / 1024)
                            break
                from api.websockets import manager as ws_manager
                tick_data['viewers'] = len(ws_manager.active_connections)
            except Exception as e:
                logger.log(f"tick metrics collection failed: {e}", level='WARNING')
            safe_broadcast("TICK", tick_data, type="tick")

            inputs = self.get_pipelines('inputs')
            if inputs is not None:
                for input in inputs:
                    try:
                        # Skip inputs that have finished
                        if input.data.state in ["EOS", "ERROR", "NULL"]:
                            continue

                        pipeline = input.get_pipeline()
                        if not pipeline:
                            continue

                        # Query position/duration (we're already in GLib thread)
                        _, state, _ = pipeline.get_state(0)
                        state_name = Gst.Element.state_get_name(state)

                        pos = -1
                        dur = -1
                        pos_success = False
                        dur_success = False

                        # 1. Query source element directly (avoids compositor returning its own timeline)
                        try:
                            pos_success, pos = pipeline.query_position(Gst.Format.TIME)
                            dur_success, dur = pipeline.query_duration(Gst.Format.TIME)
                        except Exception as e:
                            logger.log(f"Pipeline query failed for {input.data.uid}: {e}", level='DEBUG')

                        # 2. Fallback: query via video tee's sink pad (upstream to source)
                        if not pos_success or not dur_success:
                            if hasattr(input, 'video_tee') and input.video_tee:
                                sink_pad = input.video_tee.get_static_pad("sink")
                                if sink_pad:
                                    try:
                                        if not pos_success:
                                            pos_success, pos = sink_pad.query_position(Gst.Format.TIME)
                                        if not dur_success:
                                            dur_success, dur = sink_pad.query_duration(Gst.Format.TIME)
                                    except Exception as e:
                                        logger.log(f"Tee sink query failed for {input.data.uid}: {e}", level='DEBUG')

                        logger.log(f"Query {input.data.uid}: state={state_name}, pos={pos_success}/{pos}, dur={dur_success}/{dur}", level='DEBUG')

                        # Update data and schedule broadcasts
                        if pos_success and pos >= 0:
                            input.data.position = pos // Gst.SECOND
                            if hasattr(input, 'on_position_updated'):
                                input.on_position_updated()
                                safe_broadcast("UPDATE", input.data, type="input")
                            else:
                                safe_broadcast("UPDATE", PositionDTO(uid=input.data.uid, position=input.data.position), type="input")

                        if dur_success and dur > 0 and input.data.duration in [None, 0, -1]:
                            input.data.duration = dur // Gst.SECOND
                            safe_broadcast("UPDATE", input.data, type="input")
                    except Exception as e:
                        logger.log(f"Tick failed for input {input.data.uid}: {e}", level='ERROR')

            # Check output stats
            outputs = self.get_pipelines('outputs')
            if outputs is not None:
                for output in outputs:
                    try:
                        if output.data.is_preview:
                            continue
                        output.check_stats()
                    except Exception as e:
                        logger.log(f"Tick failed for output {output.data.uid}: {e}", level='ERROR')

            # Check encoder states
            encoders = self.get_pipelines('encoders')
            if encoders is not None:
                for encoder in encoders:
                    try:
                        encoder.check_state()
                    except Exception as e:
                        logger.log(f"Tick failed for encoder {encoder.data.uid}: {e}", level='ERROR')
        except Exception as e:
            logger.log(f"Tick callback error: {e}", level='ERROR')
        finally:
            # Always reschedule — tick must never stop
            self._tick()
        return False

    def start(self):
        self.mainloop = GObject.MainLoop()
        self.mainloop.run()

    def _get_category(self, pipeline) -> str:
        """Determine pipeline category from class hierarchy."""
        if is_subclass_str(pipeline.__class__, "Input"):
            return "inputs"
        elif is_subclass_str(pipeline.__class__, "Encoder"):
            return "encoders"
        elif is_subclass_str(pipeline.__class__, "Output"):
            return "outputs"
        elif is_subclass_str(pipeline.__class__, "Mixer"):
            return "mixers"
        raise KeyError("Invalid pipeline type")

    def add_pipeline(self, pipeline: "GSTBase", start=True) -> Optional[asyncio.Future]:
        """Add pipeline and broadcast CREATE. Returns a Future when scheduled from asyncio, else None."""
        if self._pipelines is None:
            self._pipelines = {"inputs": [], "outputs": [], "mixers": [], "encoders": []}

        category = self._get_category(pipeline)

        # Add to list immediately (so API can find it)
        if category not in self._pipelines:
            self._pipelines[category] = []
        self._pipelines[category].append(pipeline)

        # Add to core pipeline - use dynamic addition if already running
        if not self._defer_build and self.core_pipeline._built:
            # Pipeline already running - add dynamically without rebuild
            # Schedule on GLib thread to avoid threading issues with GStreamer
            def do_dynamic_add():
                success = False
                logger.log(f"do_dynamic_add: category={category} uid={pipeline.data.uid}", level='DEBUG')
                if category == "inputs":
                    # Pass preview creation as callback (for async sources like uridecodebin)
                    def create_preview(component):
                        self._create_preview_for_dynamic(component, category)

                    success = self.core_pipeline.add_input_dynamic(pipeline, create_preview_callback=create_preview)
                    if not success:
                        logger.log(f"Dynamic input add failed for {pipeline.data.uid}", level='ERROR')
                        pipeline.data.state = "ERROR"
                elif category == "encoders":
                    success = self.core_pipeline.add_encoder_dynamic(pipeline)
                    if not success:
                        logger.log(f"Dynamic encoder add failed for {pipeline.data.uid}", level='ERROR')
                        pipeline.data.state = "ERROR"
                elif category == "outputs":
                    if not self._ensure_output_encoders(pipeline):
                        logger.log(f"Failed to create encoder entities for output {pipeline.data.uid}", level='ERROR')
                        pipeline.data.details = pipeline.data.details or "Failed to create output encoders"
                    else:
                        success = self.core_pipeline.add_output_dynamic(pipeline)
                        if not success:
                            logger.log(f"Dynamic output add failed for {pipeline.data.uid}", level='ERROR')
                            pipeline.data.state = "ERROR"
                elif category == "mixers":
                    # Pass preview creation as callback (runs after mixer is fully set up)
                    def create_preview(component):
                        self._create_preview_for_dynamic(component, category)

                    try:
                        logger.log(f"Adding mixer dynamically: {pipeline.data.uid}", level='DEBUG')
                        success = self.core_pipeline.add_mixer_dynamic(pipeline, create_preview_callback=create_preview)
                        logger.log(f"add_mixer_dynamic returned: {success}", level='DEBUG')
                        if not success:
                            logger.log(f"Dynamic mixer add failed", level='ERROR')
                    except Exception as e:
                        logger.log(f"Exception in mixer dynamic add: {e}", level='ERROR')
                        import traceback
                        traceback.print_exc()

                if success:
                    safe_broadcast("CREATE", pipeline.data)
                else:
                    # Remove from list if dynamic add failed
                    try:
                        self._pipelines[category].remove(pipeline)
                    except ValueError:
                        pass

                return success

            # Already on GLib thread: run inline. Otherwise schedule and return future.
            ctx = GLib.MainContext.default()
            if ctx.is_owner() or not (self.mainloop and self.mainloop.is_running()):
                do_dynamic_add()
                return None
            return bridge.call_glib_async(do_dynamic_add)
        else:
            logger.log(f"Warning: add_pipeline called before finish_initial_setup for {pipeline.data.uid}", level='WARNING')
            self.core_pipeline.add_component(pipeline)
            return None

    def _add_pipeline_direct(self, pipeline):
        """Add pipeline directly (already on GLib thread). Used by _create_preview_for_dynamic."""
        category = self._get_category(pipeline)
        if category not in self._pipelines:
            self._pipelines[category] = []
        self._pipelines[category].append(pipeline)

        success = False
        if category == "encoders":
            success = self.core_pipeline.add_encoder_dynamic(pipeline)
        elif category == "outputs":
            success = self.core_pipeline.add_output_dynamic(pipeline)
        else:
            logger.log(f"_add_pipeline_direct: unsupported category {category}", level='ERROR')
            self._pipelines[category].remove(pipeline)
            return False

        if success:
            safe_broadcast("CREATE", pipeline.data)
        else:
            logger.log(f"Direct add failed for {category} {pipeline.data.uid}", level='WARNING')
            self._pipelines[category].remove(pipeline)
        return success

    def _create_preview_for_dynamic(self, pipeline, category):
        """Create preview output(s) dynamically for a running pipeline.

        Supports multiple preview types (e.g. ["webrtcbin", "hlssink2"]).
        The H.264 video encoder is shared across all preview types.
        """
        from config_handler import ConfigReader
        config = ConfigReader()

        # Check if preview is enabled for this pipeline
        if hasattr(pipeline.data, 'preview') and not pipeline.data.preview:
            logger.log(f"Preview disabled for {pipeline.data.uid}", level='DEBUG')
            return

        # Check if preview already exists
        existing = self.get_preview_pipeline(pipeline.data.uid)
        if existing:
            return

        # Determine preview config type based on category
        if category == 'inputs':
            preview_type = 'inputs'
        elif category == 'mixers':
            preview_type = 'program' if getattr(pipeline.data, 'type', None) == 'program' else 'scenes'
        else:
            logger.log(f"Unknown category {category} for preview", level='DEBUG')
            return

        preview_config = config.get_preview_config(preview_type)
        if not preview_config:
            logger.log(f"No preview config for type {preview_type}", level='DEBUG')
            return

        from pipelines.encoders.encoder import Encoder
        from api.encoder_models import EncoderEntityDTO
        from api.helper import get_auto_encoder, get_encoder_dto_class

        src_uid = pipeline.data.uid
        type_list = preview_config.get('type', [])
        if not type_list:
            return

        # Shared H.264 video encoder (created once, reused by all preview types)
        video_enc = None

        def ensure_video_encoder():
            nonlocal video_enc
            if video_enc is not None:
                return video_enc

            video_enc_element = preview_config.get('video_encoder', {}).get('name', 'auto')
            if video_enc_element == 'auto':
                video_enc_element = get_auto_encoder('h264') or 'openh264enc'
            else:
                enc_dto = get_encoder_dto_class(video_enc_element)
                pre = getattr(enc_dto, 'pre_elements', '') if enc_dto else ''
                elements_to_check = [video_enc_element] + ([pre] if pre else [])
                if not all(Gst.ElementFactory.find(e) for e in elements_to_check):
                    logger.log(f"Preview encoder {video_enc_element} not available, falling back", level='WARNING')
                    video_enc_element = get_auto_encoder('h264') or 'openh264enc'

            video_enc_options = preview_config.get('video_encoder', {}).get('options', '')
            if not video_enc_options:
                enc_cls = get_encoder_dto_class(video_enc_element)
                if enc_cls:
                    opts_field = enc_cls.model_fields.get('options')
                    video_enc_options = opts_field.default if opts_field and opts_field.default else ''

            video_enc = Encoder(data=EncoderEntityDTO(
                name="Preview Video",
                type="video", element=video_enc_element, codec="h264",
                src=src_uid, is_preview=True,
                options=video_enc_options,
                width=preview_config.get('width'), height=preview_config.get('height'),
            ))
            if not self._add_pipeline_direct(video_enc):
                video_enc = None
            return video_enc

        for ptype in type_list:
            if ptype == "webrtcbin":
                try:
                    if not ensure_video_encoder():
                        continue

                    # Skip audio encoder only when source has explicitly no audio
                    has_audio = getattr(pipeline.data, 'has_audio', True)
                    if has_audio:
                        audio_enc = Encoder(data=EncoderEntityDTO(
                            name="Preview Audio",
                            type="audio", element="opusenc",
                            src=src_uid, is_preview=True,
                            options="bitrate=64000 frame-size=10",
                        ))
                        if not self._add_pipeline_direct(audio_enc):
                            continue

                    logger.log(f"Created WebRTC preview encoders for {category} {pipeline.data.uid} (audio={has_audio})", level='DEBUG')
                except Exception as e:
                    logger.log(f"Failed to create WebRTC preview encoders for {pipeline.data.uid}: {e}", level='ERROR')
                    import traceback
                    traceback.print_exc()

            elif ptype == "hlssink2":
                from pipelines.outputs.hlssink2 import hlssink2Output
                from api.outputs.hlssink2 import hlssink2OutputDTO

                try:
                    if not ensure_video_encoder():
                        continue

                    has_audio = getattr(pipeline.data, 'has_audio', True)
                    audio_enc = None
                    if has_audio:
                        audio_enc = Encoder(data=EncoderEntityDTO(
                            name="Preview Audio",
                            type="audio", element="fdkaacenc",
                            src=src_uid, is_preview=True,
                        ))
                        if not self._add_pipeline_direct(audio_enc):
                            continue

                    preview = hlssink2Output(data=hlssink2OutputDTO(
                        name="Preview",
                        src=src_uid,
                        is_preview=True,
                        video_encoder=video_enc.data.uid,
                        audio_encoder=audio_enc.data.uid if audio_enc else None,
                    ))
                    if not self._add_pipeline_direct(preview):
                        logger.log(f"HLS preview creation failed for {pipeline.data.uid}", level='WARNING')
                    else:
                        logger.log(f"Created HLS preview {preview.data.uid} for {category} {pipeline.data.uid}", level='DEBUG')
                except Exception as e:
                    logger.log(f"Failed to create HLS preview for {pipeline.data.uid}: {e}", level='ERROR')
                    import traceback
                    traceback.print_exc()
            else:
                logger.log(f"Unsupported preview type: {ptype}", level='WARNING')

    def _ensure_output_encoders(self, output_pipeline):
        """Auto-create encoder entities from embedded encoder DTOs."""
        from pipelines.encoders.encoder import Encoder
        from api.encoder_models import EncoderEntityDTO

        data = output_pipeline.data
        auto_uids = []

        # Video encoder: if embedded DTO (not UUID), create entity
        v = getattr(data, 'video_encoder', None)
        if v and not isinstance(v, UUID):
            entity = Encoder(data=EncoderEntityDTO(
                type="video", element=v.element,
                options=v.options or "",
                codec=getattr(v, 'codec', ''),
                profile=getattr(v, 'profile', None),
                src=data.src,
                width=data.width, height=data.height,
                framerate=data.framerate,
            ))
            if self._add_pipeline_direct(entity):
                output_pipeline._video_encoder_uid = entity.data.uid
                data.video_encoder = entity.data.uid
                auto_uids.append(entity.data.uid)
            else:
                return False
        elif isinstance(v, UUID):
            output_pipeline._video_encoder_uid = v

        # Audio encoder: if embedded DTO (not UUID), create entity
        a = getattr(data, 'audio_encoder', None)
        if a and not isinstance(a, UUID):
            entity = Encoder(data=EncoderEntityDTO(
                type="audio", element=a.element,
                options=a.options or "",
                src=data.src,
                audio_filters=getattr(a, 'audio_filters', None) or [],
            ))
            if self._add_pipeline_direct(entity):
                output_pipeline._audio_encoder_uid = entity.data.uid
                data.audio_encoder = entity.data.uid
                auto_uids.append(entity.data.uid)
            else:
                return False
        elif isinstance(a, UUID):
            output_pipeline._audio_encoder_uid = a

        if auto_uids:
            output_pipeline._auto_encoder_uids = auto_uids

        return True

    def finish_initial_setup(self):
        """Build minimal pipeline to enable dynamic component addition.

        Must be called before adding any components. Creates a minimal running
        pipeline so all component additions use the same dynamic addition path,
        whether during startup or via API calls later.
        """
        self._defer_build = False
        # Build minimal pipeline
        self._ensure_core_built()

    def _ensure_core_built(self):
        """Build the core pipeline if not already built."""
        try:
            if not self.core_pipeline._built:
                self.core_pipeline.build()
        except Exception as e:
            logger.log(f"Core pipeline build failed: {e}", level='ERROR')
            import traceback
            traceback.print_exc()



    def get_pipelines(self, type):
            if self._pipelines is not None:
                return self._pipelines.get(type)
            else:
                return None

    def get_pipeline(self, type: str, uid: UUID):
        if self._pipelines is not None:
            for pipeline in self._pipelines.get(type, []):
                if pipeline.data.uid == uid:
                    return pipeline

    def get_program(self):
        if self._pipelines is not None:
            for pipeline in self._pipelines.get("mixers", []):
                if pipeline.data.type == "program":
                    return pipeline

    # return pipeline by uid
    def getpipeline(self, uid: UUID):
        for pipeline in self._pipelines.get('inputs', []):
            if pipeline.data.uid == uid:
                return pipeline
        for pipeline in self._pipelines.get('mixers', []):
            if pipeline.data.uid == uid:
                return pipeline
        for pipeline in self._pipelines.get('outputs', []):
            if pipeline.data.uid == uid:
                return pipeline
        for pipeline in self._pipelines.get('encoders', []):
            if pipeline.data.uid == uid:
                return pipeline
        return None

    def get_preview_pipeline(self, src: UUID):
        for pipeline in self._pipelines.get('outputs', []):
            if pipeline.data.src == src and pipeline.data.is_preview:
                pipeline = self.get_pipeline('outputs', pipeline.data.uid)
                return pipeline

        return None

    def _recompute_video_delays_for_src(self, src_uid):
        """Auto-sync video encoder delays to match the longest audio filter latency on this source.

        When an audio encoder adds/removes loudnorm (3s lookahead), the sibling video encoders
        on the same source need matching delay so A/V stays in sync on the encoded output.
        Preview encoders are skipped — live preview stays at zero latency.
        """
        from pipelines.audio_filters import FILTER_LATENCY_MS
        encoders = self.get_pipelines('encoders') or []

        # Compute max latency across all non-preview audio encoders on this source
        max_lat = 0
        for e in encoders:
            if e.data.type != 'audio' or getattr(e.data, 'is_preview', False):
                continue
            if e.data.src != src_uid:
                continue
            for f in (getattr(e.data, 'audio_filters', None) or []):
                if not f.enabled:
                    continue
                max_lat = max(max_lat, FILTER_LATENCY_MS.get(f.type, 0))

        logger.log(f"Video delay sync for src={src_uid}: max latency = {max_lat}ms", level='INFO')

        # Apply to every non-preview video encoder on this source
        for e in encoders:
            if e.data.type != 'video' or getattr(e.data, 'is_preview', False):
                continue
            if e.data.src != src_uid:
                continue
            current = getattr(e.data, 'video_delay_ms', 0) or 0
            if current != max_lat:
                logger.log(f"Encoder {e.data.uid} video_delay_ms: {current} → {max_lat}", level='INFO')
                e.data.video_delay_ms = max_lat
                self._patch_encoder_video_delay(e)
                safe_broadcast("UPDATE", e.data, type="encoder")

    def _patch_encoder_video_delay(self, encoder):
        """Patch the enc_delay queue min-threshold-time and max-size-time
        live on a non-preview video encoder. Runs on GLib main thread
        (callers are via GLib.idle_add)."""
        uid = encoder.data.uid
        delay_ms = getattr(encoder.data, 'video_delay_ms', 0) or 0

        elem = None
        if getattr(encoder, '_bin', None):
            elem = encoder._bin.get_by_name(f"enc_delay_{uid}")
        if not elem and self.core_pipeline and self.core_pipeline.pipeline:
            elem = self.core_pipeline.pipeline.get_by_name(f"enc_delay_{uid}")

        if not elem:
            logger.log(
                f"Encoder {uid}: enc_delay element not found — cannot patch "
                f"video_delay_ms (expected after fix)",
                level='WARNING',
            )
            return

        if delay_ms == 0:
            elem.set_property('min-threshold-time', 0)
            elem.set_property('max-size-time', 1_000_000_000)
        else:
            delay_ns = delay_ms * 1_000_000
            elem.set_property('min-threshold-time', delay_ns)
            elem.set_property('max-size-time', delay_ns + 500_000_000)
        logger.log(
            f"Encoder {uid} patched delay → {delay_ms}ms (live)",
            level='INFO',
        )

    def delete_pipeline(self, type, uid):
        pipeline = self.get_pipeline(type, uid)
        if not pipeline:
            logger.log(f"Pipeline {uid} not found for deletion", level='WARNING')
            return

        def do_delete():
            # If it's an input or mixer, also delete its preview encoders/outputs
            if type in ("inputs", "mixers"):
                self._delete_preview_pipelines(uid)

            self._delete_component(pipeline, type)

        bridge.run_sync_in_glib(do_delete)

    def _delete_preview_pipelines(self, src_uid):
        """Delete all preview encoders and outputs for a source uid."""
        # Delete all preview outputs (there may be multiple: webrtc encoders-only + hlssink2)
        for output in list(self._pipelines.get("outputs", [])):
            if getattr(output.data, 'src', None) == src_uid and getattr(output.data, 'is_preview', False):
                self._delete_component(output, "outputs")

        # Delete preview encoders
        for enc in list(self._pipelines.get("encoders", [])):
            if getattr(enc.data, 'src', None) == src_uid and getattr(enc.data, 'is_preview', False):
                self._delete_component(enc, "encoders")

        # Clean up HLS segment directory
        self._cleanup_hls_directory(src_uid)

    def _cleanup_hls_directory(self, src_uid):
        """Remove HLS segment files for a source."""
        import shutil
        from config_handler import ConfigReader
        config = ConfigReader()
        hls_dir = Path(config.get_hls_path()) / str(src_uid)
        if hls_dir.exists():
            try:
                shutil.rmtree(hls_dir)
                logger.log(f"Cleaned up HLS directory {hls_dir}", level='DEBUG')
            except Exception as e:
                logger.log(f"Failed to clean HLS directory {hls_dir}: {e}", level='WARNING')

    def _delete_component(self, pipeline, type):
        """Delete a component, clean up GStreamer resources, and broadcast DELETE."""
        uid = pipeline.data.uid
        core = self.core_pipeline.pipeline

        # If deleting an input, unlink it from any mixers first
        if type == "inputs":
            for mixer in self._pipelines.get("mixers", []):
                for i, source in enumerate(mixer.data.sources):
                    if source.src == str(uid):
                        logger.log(f"Unlinking input {uid} from mixer {mixer.data.uid} slot {i}", level='DEBUG')
                        mixer.unlink_source(i)

            # Component-specific cleanup (timers, probes, etc.)
            if hasattr(pipeline, 'cleanup'):
                try:
                    pipeline.cleanup()
                except Exception as e:
                    logger.log(f"Input cleanup error for {uid}: {e}", level='WARNING')

            # Remove pad probes
            for attr in ('_video_event_probe_id', '_audio_event_probe_id'):
                probe_id = getattr(pipeline, attr, None)
                pad = getattr(pipeline, f'{attr[:-3]}_pad', None)  # _id → _pad
                if probe_id and pad:
                    try:
                        pad.remove_probe(probe_id)
                    except Exception:
                        pass
                    setattr(pipeline, attr, None)

            # Disconnect signal handlers
            uridecodebin = getattr(pipeline, 'uridecodebin', None)
            pad_added_id = getattr(pipeline, '_pad_added_signal_id', None)
            if uridecodebin and pad_added_id:
                try:
                    uridecodebin.handler_disconnect(pad_added_id)
                except Exception:
                    pass

        # Mixer cleanup: release all slot connections
        if type == "mixers":
            if hasattr(pipeline, 'cleanup'):
                try:
                    pipeline.cleanup()
                except Exception as e:
                    logger.log(f"Mixer cleanup error for {uid}: {e}", level='WARNING')

        # Encoder cleanup: release source tee pad, source ghost pad, tee elements
        if type == "encoders" and core:
            source_tee_pad = getattr(pipeline, '_source_tee_pad', None)
            if source_tee_pad:
                parent_tee = source_tee_pad.get_parent()
                if parent_tee:
                    parent_tee.release_request_pad(source_tee_pad)

            ghost_info = getattr(pipeline, '_source_ghost_pad', None)
            if ghost_info:
                src_bin, ghost = ghost_info
                if src_bin and ghost:
                    ghost.set_active(False)
                    ghost.set_target(None)
                    src_bin.remove_pad(ghost)

            tee_elements = getattr(pipeline, '_tee_elements', None)
            if tee_elements:
                for elem in tee_elements:
                    elem.set_state(Gst.State.NULL)
                    if elem.get_parent() == core:
                        core.remove(elem)

        # Output cleanup: release tee pads, source ghost pads, auto-created encoders
        if type == "outputs" and core:
            try:
                tee_pads = getattr(pipeline, '_tee_pads', None)
                if tee_pads:
                    for key, pad in tee_pads.items():
                        parent_tee = pad.get_parent()
                        if parent_tee:
                            parent_tee.release_request_pad(pad)

                ghost_pads = getattr(pipeline, '_source_ghost_pads', None)
                if ghost_pads:
                    for key, (src_bin, ghost) in ghost_pads.items():
                        if src_bin and ghost:
                            ghost.set_active(False)
                            ghost.set_target(None)
                            src_bin.remove_pad(ghost)
            except Exception as e:
                logger.log(f"Output cleanup error for {uid}: {e}", level='ERROR')

        # Cascade: delete auto-created encoder entities for this output
        if type == "outputs":
            auto_enc_uids = getattr(pipeline, '_auto_encoder_uids', None)
            if auto_enc_uids:
                for enc_uid in auto_enc_uids:
                    enc = self.get_pipeline("encoders", enc_uid)
                    if enc:
                        logger.log(f"Cascade deleting auto-encoder {enc_uid} for output {uid}", level='DEBUG')
                        self._delete_component(enc, "encoders")

        # Lock state and remove from pipeline first (fast since locked).
        # Then NULL via GLib.idle_add (never use threading.Thread for set_state).
        component_bin = getattr(pipeline, '_bin', None)
        if component_bin and core:
            component_bin.set_locked_state(True)
            if component_bin.get_parent() == core:
                core.remove(component_bin)
            logger.log(f"Removed bin for {uid}", level='DEBUG')
            def _deferred_null_bin(b):
                try:
                    # Unlock all children so NULL propagates (e.g. playlist wpesrc chain)
                    it = b.iterate_elements()
                    done = False
                    while not done:
                        ret, elem = it.next()
                        if ret == Gst.IteratorResult.OK:
                            elem.set_locked_state(False)
                        else:
                            done = True
                    b.set_state(Gst.State.NULL)
                except Exception as e:
                    logger.log(f"Exception in deferred set_state(NULL) for {b.get_name()}: {e}", level='ERROR')
                return False
            GLib.idle_add(_deferred_null_bin, component_bin)

        # Remove from core_pipeline.components
        if uid in self.core_pipeline.components:
            del self.core_pipeline.components[uid]

        # Remove from _pipelines list
        if pipeline in self._pipelines.get(type, []):
            self._pipelines[type].remove(pipeline)

        # Broadcast DELETE
        safe_broadcast("DELETE", pipeline.data)

        logger.log(f"Deleted {type} component {uid}", level='DEBUG')


class HandlerSingleton:
    handler: ClassVar[PipelineHandler] = None

    def __new__(cls):
        if cls.handler is None:
            cls.handler = PipelineHandler()

        return cls.handler