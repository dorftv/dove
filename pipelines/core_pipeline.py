from typing import Optional
from uuid import UUID
from gi.repository import Gst, GLib
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr
from logger import logger
from event_loop_bridge import safe_broadcast


class CorePipeline(BaseModel):
    """Manages the single core pipeline containing all inputs, mixers, and outputs."""

    pipeline: Optional[Gst.Pipeline] = None
    components: dict = Field(default_factory=dict)  # uid -> component
    _built: bool = PrivateAttr(default=False)
    _building: bool = PrivateAttr(default=False)
    _pending_levels: dict = PrivateAttr(default_factory=dict)
    _level_timer_id: Optional[int] = PrivateAttr(default=None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def build(self):
        """Concatenate all component strings and launch single pipeline."""
        if self._built:
            logger.log("Core pipeline already built, skipping", level='DEBUG')
            return

        if self._building:
            logger.log("Core pipeline build already in progress, skipping", level='DEBUG')
            return

        self._building = True
        ordered = self._get_ordered_components()
        logger.log(f"Building core pipeline with {len(ordered)} components", level='DEBUG')

        # Separate components into string-based and bin-based
        deferred = []  # Components that need dynamic add (use build_bin())
        pipeline_str = ""
        for component in ordered:
            try:
                fragment = component.build_pipeline_str()
                logger.log(f"  Component {component.data.uid} ({component.__class__.__name__})", level='DEBUG')
                pipeline_str += fragment
            except NotImplementedError:
                logger.log(f"  Deferring {component.data.uid} ({component.__class__.__name__}) - uses build_bin()", level='DEBUG')
                deferred.append(component)

        if not pipeline_str:
            logger.log("No string components - creating empty pipeline", level='DEBUG')
            self.pipeline = Gst.Pipeline.new("core_pipeline")
        else:
            logger.log(f"Core pipeline string: {pipeline_str}", level='DEBUG')
            try:
                self.pipeline = Gst.parse_launch(pipeline_str)
                logger.log("Pipeline parsed successfully", level='DEBUG')
            except Exception as e:
                logger.log(f"Pipeline parse failed: {e}", level='ERROR')
                self._building = False
                raise

        # Attach all components (get element references)
        try:
            for component in self.components.values():
                logger.log(f"Attaching component {component.data.uid}", level='DEBUG')
                component.attach(self.pipeline)
            logger.log(f"All {len(self.components)} components attached", level='DEBUG')
        except Exception as e:
            logger.log(f"Component attach failed: {e}", level='ERROR')
            self._building = False
            raise

        # Set up bus handlers
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self._on_error)
        bus.connect("message::eos", self._on_eos)
        bus.connect("message::state-changed", self._on_state_change)
        bus.connect("message::element", self._on_element_message)
        bus.connect("message::buffering", self._on_buffering)
        logger.log("Bus handlers connected", level='DEBUG')

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        logger.log(f"Set state to PLAYING returned: {ret}", level='DEBUG')

        # Wait for pipeline to reach PLAYING state before allowing dynamic additions
        if ret == Gst.StateChangeReturn.ASYNC:
            logger.log("Waiting for pipeline to reach PLAYING state...", level='DEBUG')
            result, state, pending = self.pipeline.get_state(5 * Gst.SECOND)  # 5 second timeout
            if result == Gst.StateChangeReturn.SUCCESS:
                logger.log(f"Pipeline reached state: {Gst.Element.state_get_name(state)}", level='DEBUG')
            else:
                logger.log(f"Pipeline state change timeout/failure: {result}", level='WARNING')

        self._built = True
        self._building = False
        logger.log("Core pipeline build complete", level='DEBUG')

        # Add deferred components (those using build_bin()) dynamically
        if deferred:
            logger.log(f"Adding {len(deferred)} deferred components dynamically", level='DEBUG')
            from pipelines.inputs.input import Input
            from pipelines.encoders.encoder import Encoder
            from pipelines.outputs.output import Output
            for component in deferred:
                try:
                    if isinstance(component, Input):
                        self.add_input_dynamic(component)
                    elif isinstance(component, Encoder):
                        self.add_encoder_dynamic(component)
                    elif isinstance(component, Output):
                        self.add_output_dynamic(component)
                    logger.log(f"  Deferred add OK: {component.data.uid}", level='DEBUG')
                except Exception as e:
                    logger.log(f"  Deferred add failed {component.data.uid}: {e}", level='ERROR')
                    component.data.state = "ERROR"
                    safe_broadcast("UPDATE", component.data)

    def _get_ordered_components(self):
        """Return components in order: inputs, mixers, encoders, outputs."""
        from pipelines.inputs.input import Input
        from pipelines.mixers.mixer import Mixer
        from pipelines.encoders.encoder import Encoder
        from pipelines.outputs.output import Output

        inputs = [c for c in self.components.values() if isinstance(c, Input)]
        mixers = [c for c in self.components.values() if isinstance(c, Mixer)]
        encoders = [c for c in self.components.values() if isinstance(c, Encoder)]
        outputs = [c for c in self.components.values() if isinstance(c, Output)]
        return inputs + mixers + encoders + outputs

    def add_component(self, component):
        """Register a component (does not add to GStreamer pipeline — use add_*_dynamic)."""
        self.components[component.data.uid] = component

    def add_input_dynamic(self, input_component, create_preview_callback=None):
        """Add an input bin to a running pipeline without rebuild."""
        if not self._built or not self.pipeline:
            self.components[input_component.data.uid] = input_component
            return False

        uid = input_component.data.uid

        try:
            # Check if component has build_bin() method (for complex sources like uridecodebin3)
            if hasattr(input_component, 'build_bin') and callable(input_component.build_bin):
                input_bin = input_component.build_bin()
                # References are set by build_bin()
            else:
                # Use pipeline string for simple sources
                pipeline_str = input_component.build_pipeline_str()
                input_bin = Gst.parse_bin_from_description(pipeline_str, False)
                input_bin.set_name(f"input_bin_{uid}")
                # Get element references from inside the bin
                input_component.video_tee = input_bin.get_by_name(f"video_tee_{uid}")
                input_component.audio_tee = input_bin.get_by_name(f"audio_tee_{uid}")
                input_component.input_videomixer = input_bin.get_by_name(f"input_videomixer_{uid}")
                input_component.input_audiomixer = input_bin.get_by_name(f"input_audiomixer_{uid}")
                input_component.volume_element = input_bin.get_by_name(f"volume_{uid}")

            logger.log(f"Input bin tees: video={input_component.video_tee}, audio={input_component.audio_tee}", level='DEBUG')

            # Add bin to pipeline
            self.pipeline.add(input_bin)

            # Store references
            self.components[uid] = input_component
            input_component._bin = input_bin

            # cefsrc blocks in start() during CefBrowserHost::CreateBrowserSync().
            # Run state change on worker thread to avoid freezing the GLib main loop.
            # Serialize cefsrc inits — CEF race condition if two start simultaneously.
            needs_async_state = input_bin.get_by_name(f"cefsrc_{uid}") is not None

            if needs_async_state:
                input_component.data.state = "PENDING"
                safe_broadcast("UPDATE", input_component.data)
                import threading
                if not hasattr(self, '_cef_init_lock'):
                    self._cef_init_lock = threading.Lock()
                cef_lock = self._cef_init_lock
                def _blocking_state_change():
                    try:
                        with cef_lock:
                            logger.log(f"cefsrc {uid} worker thread started, calling sync_state_with_parent", level='DEBUG')
                            ret = input_bin.sync_state_with_parent()
                            logger.log(f"cefsrc {uid} sync_state_with_parent returned: {ret}", level='DEBUG')
                        def _finalize():
                            if uid not in self.components:
                                return False
                            result, state, pending = input_bin.get_state(100 * Gst.MSECOND)
                            if result == Gst.StateChangeReturn.SUCCESS:
                                input_component.data.state = Gst.Element.state_get_name(state)
                            else:
                                input_component.data.state = "PLAYING"
                            safe_broadcast("UPDATE", input_component.data)
                            if create_preview_callback:
                                GLib.timeout_add(500, lambda: (create_preview_callback(input_component), False)[-1])
                            return False
                        GLib.idle_add(_finalize)
                    except Exception as e:
                        logger.log(f"cefsrc state change failed for {uid}: {e}", level='ERROR')
                threading.Thread(target=_blocking_state_change, daemon=True).start()
            else:
                # Sync state with parent pipeline
                ret = input_bin.sync_state_with_parent()
                logger.log(f"Input bin {uid} sync_state_with_parent returned: {ret}", level='DEBUG')

                # Wait for state transition with timeout, or set PENDING
                result, state, pending = input_bin.get_state(100 * Gst.MSECOND)
                if result == Gst.StateChangeReturn.SUCCESS:
                    input_component.data.state = Gst.Element.state_get_name(state)
                else:
                    input_component.data.state = "PENDING"  # Let bus callback update when ready
                safe_broadcast("UPDATE", input_component.data)

                # Create preview if callback provided - schedule for later to avoid deadlock
                if create_preview_callback:
                    def delayed_preview_callback():
                        if uid not in self.components:
                            logger.log(f"Preview callback skipped — {uid} already deleted", level='DEBUG')
                            return False
                        try:
                            logger.log(f"Delayed preview callback firing for {uid}", level='DEBUG')
                            create_preview_callback(input_component)
                        except Exception as e:
                            logger.log(f"Preview callback error for {uid}: {e}", level='ERROR')
                            import traceback
                            logger.log(traceback.format_exc(), level='ERROR')
                        return False  # Don't repeat
                    GLib.timeout_add(500, delayed_preview_callback)

            logger.log(f"Dynamically added input bin {uid}", level='DEBUG')
            return True

        except Exception as e:
            input_component.data.details = str(e)
            logger.log(f"Failed to add input dynamically: {e}", level='ERROR')
            import traceback
            logger.log(traceback.format_exc(), level='ERROR')

            # Rollback: clean up partial state
            try:
                if 'input_bin' in locals() and input_bin:
                    input_bin.set_state(Gst.State.NULL)
                    if input_bin.get_parent() == self.pipeline:
                        self.pipeline.remove(input_bin)
                if uid in self.components:
                    del self.components[uid]
                input_component._bin = None
                logger.log(f"Rolled back partial input add for {uid}", level='DEBUG')
            except Exception as rollback_error:
                logger.log(f"Rollback failed: {rollback_error}", level='ERROR')

            return False

    def add_mixer_dynamic(self, mixer_component, create_preview_callback=None):
        """Add a mixer bin to a running pipeline without rebuild."""
        if not self._built or not self.pipeline:
            self.components[mixer_component.data.uid] = mixer_component
            return False

        uid = mixer_component.data.uid

        try:
            pipeline_str = mixer_component.build_pipeline_str()
            mixer_bin = Gst.parse_bin_from_description(pipeline_str, False)
            mixer_bin.set_name(f"mixer_bin_{uid}")
            mixer_component.video_mixer = mixer_bin.get_by_name(f"videomixer_{uid}")
            mixer_component.audio_mixer = mixer_bin.get_by_name(f"audiomixer_{uid}")
            mixer_component._slot_queues = {}
            mixer_component._tee_pads = {}
            mixer_component._ghost_pads = {}

            logger.log(f"Mixer bin elements: video_mixer={mixer_component.video_mixer}, audio_mixer={mixer_component.audio_mixer}", level='DEBUG')

            # Add bin to pipeline
            self.pipeline.add(mixer_bin)

            # Store references
            self.components[uid] = mixer_component
            mixer_component._bin = mixer_bin
            mixer_component.core_pipeline = self.pipeline

            # Sync state with parent pipeline (should go to PLAYING)
            ret = mixer_bin.sync_state_with_parent()
            logger.log(f"Mixer bin {uid} sync_state_with_parent returned: {ret}", level='DEBUG')

            # Check actual state
            success, state, pending = mixer_bin.get_state(0)
            logger.log(f"Mixer bin {uid} state after sync: {Gst.Element.state_get_name(state)}, pending: {Gst.Element.state_get_name(pending)}", level='DEBUG')

            # Check pipeline state
            _, pipe_state, pipe_pending = self.pipeline.get_state(0)
            logger.log(f"Pipeline state after mixer add: {Gst.Element.state_get_name(pipe_state)}, pending: {Gst.Element.state_get_name(pipe_pending)}", level='DEBUG')

            # Wait for state transition with timeout, or set PENDING
            result, state, pending = mixer_bin.get_state(100 * Gst.MSECOND)
            if result == Gst.StateChangeReturn.SUCCESS:
                mixer_component.data.state = Gst.Element.state_get_name(state)
            else:
                mixer_component.data.state = "PENDING"  # Let bus callback update when ready
            safe_broadcast("UPDATE", mixer_component.data)

            # Create initial slots based on mixer type
            if mixer_component.data.type == 'program':
                # Program mixer needs 2 slots for A/B switching
                mixer_component.add_slot()
                mixer_component.add_slot()
            else:
                # Scene mixers use 'n' to configure slot count
                n = getattr(mixer_component.data, 'n', 0) or 0
                for i in range(n):
                    mixer_component.add_slot()

            logger.log(f"Dynamically added mixer bin {uid}", level='DEBUG')

            # Create preview if callback provided (after mixer is fully set up)
            if create_preview_callback:
                create_preview_callback(mixer_component)

            return True

        except Exception as e:
            mixer_component.data.details = str(e)
            logger.log(f"Failed to add mixer dynamically: {e}", level='ERROR')
            import traceback
            logger.log(traceback.format_exc(), level='ERROR')

            # Rollback: clean up partial state
            try:
                if 'mixer_bin' in locals() and mixer_bin:
                    mixer_bin.set_state(Gst.State.NULL)
                    if mixer_bin.get_parent() == self.pipeline:
                        self.pipeline.remove(mixer_bin)
                if uid in self.components:
                    del self.components[uid]
                mixer_component._bin = None
                mixer_component.video_mixer = None
                mixer_component.audio_mixer = None
                logger.log(f"Rolled back partial mixer add for {uid}", level='DEBUG')
            except Exception as rollback_error:
                logger.log(f"Rollback failed: {rollback_error}", level='ERROR')

            return False

    def add_output_dynamic(self, output_component):
        """Add an output bin to running pipeline, linking to source or encoder tees.

        Supports full (video+audio), video-only, and audio-only outputs.
        Uses _video_encoder_uid / _audio_encoder_uid attributes (set by
        _ensure_output_encoders) to determine per-stream tee connections.
        """
        if not self._built or not self.pipeline:
            self.components[output_component.data.uid] = output_component
            return False

        from pipelines.inputs.input import Input
        from pipelines.mixers.mixer import Mixer
        from pipelines.encoders.encoder import Encoder

        uid = output_component.data.uid

        # Determine per-stream tee and source bin
        video_encoder_uid = getattr(output_component, '_video_encoder_uid', None)
        audio_encoder_uid = getattr(output_component, '_audio_encoder_uid', None)

        # Also check data for UUID encoder refs (srtsink/hlssink2 pattern)
        if not video_encoder_uid and isinstance(output_component.data.video_encoder, UUID):
            video_encoder_uid = output_component.data.video_encoder
        if not audio_encoder_uid and isinstance(output_component.data.audio_encoder, UUID):
            audio_encoder_uid = output_component.data.audio_encoder

        video_tee = None
        audio_tee = None
        video_source_bin = None
        audio_source_bin = None

        # Resolve video tee
        if video_encoder_uid:
            enc = self.components.get(video_encoder_uid)
            if not enc or not isinstance(enc, Encoder):
                logger.log(f"Video encoder entity not found: {video_encoder_uid}", level='ERROR')
                return False
            video_tee = enc.tee
            video_source_bin = None  # Encoder tees are at pipeline level
            if not video_tee:
                logger.log(f"Video encoder tee not found for {video_encoder_uid}", level='ERROR')
                return False

        if audio_encoder_uid:
            enc = self.components.get(audio_encoder_uid)
            if not enc or not isinstance(enc, Encoder):
                logger.log(f"Audio encoder entity not found: {audio_encoder_uid}", level='ERROR')
                return False
            audio_tee = enc.tee
            audio_source_bin = None
            if not audio_tee:
                logger.log(f"Audio encoder tee not found for {audio_encoder_uid}", level='ERROR')
                return False

        # For streams without encoder, fall back to source tees
        src_uid = output_component.data.src
        if (not video_tee or not audio_tee) and src_uid:
            src_component = self.components.get(src_uid)
            if not src_component:
                logger.log(f"Source component not found: {src_uid}", level='ERROR')
                return False

            if isinstance(src_component, Input):
                if not video_tee:
                    video_tee = src_component.video_tee
                    video_source_bin = getattr(src_component, '_bin', None)
                if not audio_tee:
                    audio_tee = src_component.audio_tee
                    audio_source_bin = getattr(src_component, '_bin', None)
            elif isinstance(src_component, Mixer):
                source_bin = getattr(src_component, '_bin', None)
                if not video_tee:
                    video_source_bin = source_bin
                    if source_bin:
                        video_tee = source_bin.get_by_name(f"scene_video_tee_{src_uid}")
                    else:
                        video_tee = self.pipeline.get_by_name(f"scene_video_tee_{src_uid}")
                if not audio_tee:
                    audio_source_bin = source_bin
                    if source_bin:
                        audio_tee = source_bin.get_by_name(f"scene_audio_tee_{src_uid}")
                    else:
                        audio_tee = self.pipeline.get_by_name(f"scene_audio_tee_{src_uid}")
            else:
                logger.log(f"Unknown source type for {src_uid}", level='ERROR')
                return False

        try:
            # Build output bin string (dynamic=True for named queues)
            pipeline_str = output_component.build_pipeline_str(dynamic=True)
            logger.log(f"Output {uid} dynamic pipeline: {pipeline_str}", level='DEBUG')

            output_bin = Gst.parse_bin_from_description(pipeline_str, False)
            output_bin.set_name(f"output_bin_{uid}")
            output_bin.set_property("async-handling", True)

            # Detect which streams this output has
            video_queue = output_bin.get_by_name(f"video_queue_{uid}")
            audio_queue = output_bin.get_by_name(f"audio_queue_{uid}")
            has_video = video_queue is not None
            has_audio = audio_queue is not None

            if not has_video and not has_audio:
                logger.log(f"Output {uid} has no video or audio queues", level='ERROR')
                return False

            # Validate required tees exist
            if has_video and not video_tee:
                logger.log(f"Output {uid} needs video tee but none found", level='ERROR')
                return False
            if has_audio and not audio_tee:
                logger.log(f"Output {uid} needs audio tee but none found", level='ERROR')
                return False

            tee_pads = {}
            source_ghost_pads = {}

            # Set up queues: small + leaky for isolation (prevent backpressure on shared tees)
            if has_video:
                video_queue.set_property("leaky", 2)  # downstream: drop oldest
                video_queue.set_property("max-size-buffers", 5)
                video_queue.set_property("max-size-time", 0)
                video_queue.set_property("max-size-bytes", 0)
                video_ghost = Gst.GhostPad.new("video_sink", video_queue.get_static_pad("sink"))
                video_ghost.set_active(True)
                output_bin.add_pad(video_ghost)

            if has_audio:
                audio_queue.set_property("leaky", 2)  # downstream: drop oldest
                audio_queue.set_property("max-size-buffers", 5)
                audio_queue.set_property("max-size-time", 0)
                audio_queue.set_property("max-size-bytes", 0)
                audio_ghost = Gst.GhostPad.new("audio_sink", audio_queue.get_static_pad("sink"))
                audio_ghost.set_active(True)
                output_bin.add_pad(audio_ghost)

            self.pipeline.add(output_bin)

            # Let component connect signals before state change
            output_component.connect_signals(self.pipeline)

            # Sync state BEFORE linking tee pads — ensures queue is PLAYING
            # so tee pads don't get FLUSHING returns that kill other consumers
            output_bin.sync_state_with_parent()

            # Link video
            if has_video:
                video_tee_pad = video_tee.request_pad_simple("src_%u")
                tee_pads['video'] = video_tee_pad
                if video_source_bin:
                    video_source_ghost = Gst.GhostPad.new(f"video_out_{uid}", video_tee_pad)
                    video_source_ghost.set_active(True)
                    video_source_bin.add_pad(video_source_ghost)
                    link_result_v = video_source_ghost.link(video_ghost)
                    source_ghost_pads['video'] = (video_source_bin, video_source_ghost)
                else:
                    link_result_v = video_tee_pad.link(video_ghost)
                logger.log(f"Video link result: {link_result_v}", level='DEBUG')
                if link_result_v != Gst.PadLinkReturn.OK:
                    logger.log(f"Video link FAILED: {link_result_v}", level='ERROR')

            # Link audio
            if has_audio:
                audio_tee_pad = audio_tee.request_pad_simple("src_%u")
                tee_pads['audio'] = audio_tee_pad
                if audio_source_bin:
                    audio_source_ghost = Gst.GhostPad.new(f"audio_out_{uid}", audio_tee_pad)
                    audio_source_ghost.set_active(True)
                    audio_source_bin.add_pad(audio_source_ghost)
                    link_result_a = audio_source_ghost.link(audio_ghost)
                    source_ghost_pads['audio'] = (audio_source_bin, audio_source_ghost)
                else:
                    link_result_a = audio_tee_pad.link(audio_ghost)
                logger.log(f"Audio link result: {link_result_a}", level='DEBUG')
                if link_result_a != Gst.PadLinkReturn.OK:
                    logger.log(f"Audio link FAILED: {link_result_a}", level='ERROR')

            # Store references
            self.components[uid] = output_component
            output_component._bin = output_bin
            output_component._tee_pads = tee_pads
            if source_ghost_pads:
                output_component._source_ghost_pads = source_ghost_pads

            output_component.data.state = "PENDING"
            safe_broadcast("UPDATE", output_component.data)

            logger.log(f"Dynamically added output bin {uid}", level='DEBUG')
            return True

        except Exception as e:
            output_component.data.details = str(e)
            logger.log(f"Failed to add output dynamically: {e}", level='ERROR')
            import traceback
            logger.log(traceback.format_exc(), level='ERROR')

            try:
                for key, (src_bin, ghost) in source_ghost_pads.items():
                    if src_bin and ghost:
                        ghost.set_active(False)
                        ghost.set_target(None)
                        src_bin.remove_pad(ghost)
                for key, pad in tee_pads.items():
                    parent = pad.get_parent()
                    if parent:
                        parent.release_request_pad(pad)
                if 'output_bin' in locals() and output_bin:
                    output_bin.set_state(Gst.State.NULL)
                    if output_bin.get_parent() == self.pipeline:
                        self.pipeline.remove(output_bin)
                if uid in self.components:
                    del self.components[uid]
                output_component._bin = None
                logger.log(f"Rolled back partial output add for {uid}", level='DEBUG')
            except Exception as rollback_error:
                logger.log(f"Rollback failed: {rollback_error}", level='ERROR')

            return False

    def add_encoder_dynamic(self, encoder_component):
        """Add an encoder bin to running pipeline, linking to source tees.

        Architecture: encoder bin (auto ghost pads) → top-level tee → queue → fakesink.
        The tee lives at pipeline level so consumers (outputs, WHEP) can link directly
        without ghost pads on the encoder bin.
        """
        if not self._built or not self.pipeline:
            self.components[encoder_component.data.uid] = encoder_component
            return False

        from pipelines.inputs.input import Input
        from pipelines.mixers.mixer import Mixer

        src_uid = encoder_component.data.src
        if not src_uid:
            logger.log(f"Encoder {encoder_component.data.uid} has no src", level='ERROR')
            return False

        src_component = self.components.get(src_uid)
        if not src_component:
            logger.log(f"Encoder source not found: {src_uid}", level='ERROR')
            return False

        # Find the appropriate source tee (video or audio)
        media_type = encoder_component.data.type  # "video" or "audio"
        source_bin = getattr(src_component, '_bin', None)

        if isinstance(src_component, Input):
            if media_type == "video":
                source_tee = src_component.video_tee
            else:
                source_tee = src_component.audio_tee
        elif isinstance(src_component, Mixer):
            tee_prefix = "scene_video_tee" if media_type == "video" else "scene_audio_tee"
            if source_bin:
                source_tee = source_bin.get_by_name(f"{tee_prefix}_{src_uid}")
            else:
                source_tee = self.pipeline.get_by_name(f"{tee_prefix}_{src_uid}")
        else:
            logger.log("Unknown source type for encoder", level='ERROR')
            return False

        if not source_tee:
            logger.log(f"Source tee not found for encoder {encoder_component.data.uid}", level='ERROR')
            return False

        uid = encoder_component.data.uid
        encoder_bin = None
        enc_tee = None
        enc_queue = None
        enc_fakesink = None
        tee_pad = None
        source_ghost = None

        try:
            pipeline_str = encoder_component.build_pipeline_str()
            logger.log(f"Encoder {uid} pipeline: {pipeline_str}", level='DEBUG')

            # Auto ghost pads: sink (from queue) and src (from last element)
            encoder_bin = Gst.parse_bin_from_description(pipeline_str, True)
            encoder_bin.set_name(f"encoder_bin_{uid}")
            encoder_bin.set_property("async-handling", True)

            # Create top-level tee + queue + fakesink
            enc_tee = Gst.ElementFactory.make("tee", f"enc_tee_{uid}")
            enc_tee.set_property("allow-not-linked", True)
            enc_queue = Gst.ElementFactory.make("queue", f"enc_tee_q_{uid}")
            enc_queue.set_property("leaky", 2)  # downstream: drop oldest
            enc_fakesink = Gst.ElementFactory.make("fakesink", f"enc_tee_fs_{uid}")
            enc_fakesink.set_property("async", False)

            # Store refs early so rollback can find them
            encoder_component._tee_elements = [enc_tee, enc_queue, enc_fakesink]
            encoder_component._bin = encoder_bin

            # Add all to pipeline
            self.pipeline.add(encoder_bin)
            self.pipeline.add(enc_tee)
            self.pipeline.add(enc_queue)
            self.pipeline.add(enc_fakesink)

            # Link encoder bin → tee → queue → fakesink
            if not encoder_bin.link(enc_tee):
                raise RuntimeError("encoder_bin -> enc_tee link failed")
            if not enc_tee.link(enc_queue):
                raise RuntimeError("enc_tee -> enc_queue link failed")
            if not enc_queue.link(enc_fakesink):
                raise RuntimeError("enc_queue -> enc_fakesink link failed")

            # Request pad from source tee and link to encoder bin's ghost sink
            tee_pad = source_tee.request_pad_simple("src_%u")

            if source_bin:
                # Source is in a bin — need ghost pad on source bin
                source_ghost = Gst.GhostPad.new(f"enc_out_{uid}", tee_pad)
                source_ghost.set_active(True)
                source_bin.add_pad(source_ghost)
                link_result = source_ghost.link(encoder_bin.get_static_pad("sink"))
                encoder_component._source_ghost_pad = (source_bin, source_ghost)
            else:
                link_result = tee_pad.link(encoder_bin.get_static_pad("sink"))

            logger.log(f"Encoder link result: {link_result}", level='DEBUG')

            # Store remaining references
            self.components[uid] = encoder_component
            encoder_component._source_tee_pad = tee_pad
            encoder_component.tee = enc_tee

            # Block latency queries from encoder internals (e.g. audioloudnorm 3s)
            # so they don't inflate pipeline-wide latency and delay previews.
            encoder_component.install_latency_firewall()

            # Sync state: downstream first (sink → source)
            enc_fakesink.sync_state_with_parent()
            enc_queue.sync_state_with_parent()
            enc_tee.sync_state_with_parent()
            encoder_bin.sync_state_with_parent()
            encoder_component.data.state = "PLAYING"
            from event_loop_bridge import safe_broadcast
            safe_broadcast("UPDATE", encoder_component.data, type="encoder")

            # Apply initial audio filters if configured (e.g. from config.toml)
            initial_filters = getattr(encoder_component.data, 'audio_filters', None)
            if initial_filters and encoder_component.data.type == 'audio' and not getattr(encoder_component.data, 'is_preview', False):
                GLib.idle_add(encoder_component._rebuild_audio_filter_chain, initial_filters)

            logger.log(f"Dynamically added encoder {uid}", level='DEBUG')
            return True

        except Exception as e:
            encoder_component.data.details = str(e)
            logger.log(f"Failed to add encoder dynamically: {e}", level='ERROR')
            import traceback
            logger.log(traceback.format_exc(), level='ERROR')

            try:
                # Rollback: clean up tee elements
                for el in (enc_tee, enc_queue, enc_fakesink):
                    if el and el.get_parent() == self.pipeline:
                        el.set_state(Gst.State.NULL)
                        self.pipeline.remove(el)
                # Rollback: release source tee pad
                if tee_pad:
                    source_tee.release_request_pad(tee_pad)
                # Rollback: remove source ghost pad
                if source_ghost and source_bin:
                    source_ghost.set_target(None)
                    source_ghost.set_active(False)
                    source_bin.remove_pad(source_ghost)
                # Rollback: remove encoder bin
                if encoder_bin:
                    encoder_bin.set_state(Gst.State.NULL)
                    if encoder_bin.get_parent() == self.pipeline:
                        self.pipeline.remove(encoder_bin)
                if uid in self.components:
                    del self.components[uid]
                encoder_component._bin = None
                encoder_component.tee = None
                encoder_component._tee_elements = None
            except Exception as rollback_error:
                logger.log(f"Encoder rollback failed: {rollback_error}", level='ERROR')

            return False

    def get_element(self, name: str):
        """Get element by name from the pipeline."""
        if self.pipeline:
            return self.pipeline.get_by_name(name)
        return None

    def add_element(self, element: Gst.Element):
        """Add element to running pipeline."""
        if self.pipeline:
            self.pipeline.add(element)
            element.sync_state_with_parent()

    def _find_component_for_element(self, element):
        """Find which component an element belongs to by checking element name and parent hierarchy."""
        if element is None:
            return None

        # Search current element and all parents up to pipeline
        current = element
        while current is not None and not isinstance(current, Gst.Pipeline):
            element_name = current.get_name()
            if element_name:
                # Element names contain the component uid (e.g., "video_tee_uuid", "uridecodebin_uuid")
                for uid, component in self.components.items():
                    uid_str = str(uid)
                    if uid_str in element_name:
                        return component

            # Move to parent
            current = current.get_parent()

        return None

    def _on_error(self, bus, message):
        try:
            err, debug = message.parse_error()
            element = message.src
            component = self._find_component_for_element(element)

            if component:
                # Suppress transient errors during source teardown (e.g. playlist clip change)
                if getattr(component, '_suppress_teardown_error', False):
                    debug_str = debug or ''
                    if any(s in debug_str for s in ('not-linked', 'No streams to output', 'No suitable plugins found')):
                        logger.log(f"Component {component.data.uid} suppressed teardown error: {err.message}", level='DEBUG')
                        return
                # Let playlist recover from per-clip errors
                if hasattr(component, 'handle_error'):
                    component.handle_error(err.message)
                    if component.data.state == "ERROR":
                        GLib.idle_add(lambda uid=component.data.uid: self._mute_errored_source(uid) or False)
                    return
                logger.log(f"Component {component.data.uid} error: {err.message}", level='ERROR')
                component.data.state = "ERROR"
                component.data.details = f"Error: {err.message}" + (f"\n{debug}" if debug else "")
                safe_broadcast("UPDATE", component.data)
                # Auto-mute errored input in all mixers (deferred to avoid
                # interfering with error handling on the bus thread)
                GLib.idle_add(lambda uid=component.data.uid: self._mute_errored_source(uid) or False)
            else:
                logger.log(f"Pipeline error: {err.message}\n{debug}", level='ERROR')
        except Exception as e:
            logger.log(f"Exception in _on_error handler: {e}", level='ERROR')

    def _mute_errored_source(self, source_uid):
        """Mute an errored input in all mixers that reference it."""
        from pipeline_handler import HandlerSingleton
        try:
            handler = HandlerSingleton()
            for mixer in handler.get_pipelines('mixers') or []:
                mixer.mute_source(source_uid)
        except Exception as e:
            logger.log(f"Failed to mute errored source {source_uid}: {e}", level='ERROR')

    def _on_eos(self, bus, message):
        """Handle EOS — delegate to component first (e.g., looping)."""
        try:
            element = message.src
            component = self._find_component_for_element(element)

            if component:
                # Let component handle EOS first (e.g., looping via flush seek)
                if hasattr(component, 'handle_eos') and component.handle_eos():
                    return
                logger.log(f"Component {component.data.uid} reached EOS", level='DEBUG')
                component.data.state = "EOS"
                safe_broadcast("UPDATE", component.data)
            else:
                logger.log(f"Pipeline EOS from {element.get_name() if element else 'unknown'}", level='DEBUG')
        except Exception as e:
            logger.log(f"Exception in _on_eos handler: {e}", level='ERROR')

    def _on_state_change(self, bus, message):
        try:
            old, new, pending = message.parse_state_changed()
            old_name = Gst.Element.state_get_name(old)
            new_name = Gst.Element.state_get_name(new)
            pending_name = Gst.Element.state_get_name(pending)

            src_name = message.src.get_name() if message.src else "unknown"
            src_type = type(message.src).__name__

            # Only log top-level bin state changes (skip internal sub-elements)
            if src_name.startswith(("input_bin_", "mixer_bin_", "encoder_bin_", "output_bin_")):
                logger.log(f"State change: {src_name} {old_name} -> {new_name} (pending: {pending_name})", level='DEBUG')

            # Handle core pipeline state changes
            if isinstance(message.src, Gst.Pipeline):
                logger.log(f"Core pipeline state: {old_name} -> {new_name} (pending: {pending_name}, components: {len(self.components)})", level='DEBUG')

                # Only broadcast PLAYING state to avoid false PAUSED broadcasts during dynamic addition
                if new_name == "PLAYING":
                    for component in self.components.values():
                        # Only update if not in a special state (ERROR, EOS)
                        if component.data.state not in ["ERROR", "EOS"]:
                            component.data.state = new_name
                            safe_broadcast("UPDATE", component.data)
                    logger.log(f"Broadcasted state {new_name} to {len(self.components)} components", level='DEBUG')

            # Handle bin state changes — only for top-level bins (direct pipeline children).
            # Internal sub-elements (decodebin3, parsebin, urisourcebin) generate many
            # state changes during _stop_source; processing them all floods the GLib loop.
            elif isinstance(message.src, Gst.Bin):
                parent = message.src.get_parent()
                if parent != self.pipeline:
                    return  # Skip internal sub-element state changes

                component = self._find_component_for_element(message.src)
                if component:
                    # Only broadcast significant state changes for this component
                    if new_name in ["PLAYING", "PAUSED", "READY", "NULL"]:
                        # Don't overwrite special states
                        if component.data.state not in ["ERROR", "EOS"]:
                            component.data.state = new_name
                            safe_broadcast("UPDATE", component.data)
                            logger.log(f"Component {component.data.uid} state: {old_name} -> {new_name}", level='DEBUG')
        except Exception as e:
            logger.log(f"Exception in _on_state_change handler: {e}", level='ERROR')

    def _on_element_message(self, bus, message):
        """Handle element messages — batch audio levels for periodic broadcast."""
        try:
            structure = message.get_structure()
            if not structure or structure.get_name() != "level":
                return
            element_name = message.src.get_name()
            if not element_name.startswith("level_"):
                return
            uid = element_name[6:]
            rms = structure.get_value("rms")
            if not rms:
                return
            left = self._db_to_percent(rms[0]) if len(rms) > 0 else 0
            right = self._db_to_percent(rms[1]) if len(rms) > 1 else left
            self._pending_levels[uid] = {"uid": uid, "left": left, "right": right}
            if self._level_timer_id is None:
                self._level_timer_id = GLib.timeout_add(200, self._flush_levels)
        except Exception as e:
            logger.log(f"Exception in _on_element_message: {e}", level='ERROR')

    def _on_buffering(self, bus, message):
        """Handle buffering messages from uridecodebin3 — broadcast to frontend."""
        try:
            percent = message.parse_buffering()
            component = self._find_component_for_element(message.src)
            if component:
                component.data.buffering = percent
                if percent < 100:
                    component.data.state = "BUFFERING"
                elif component.data.state == "BUFFERING":
                    component.data.state = "PLAYING"
                safe_broadcast("UPDATE", component.data)
        except Exception as e:
            logger.log(f"Exception in _on_buffering handler: {e}", level='ERROR')

    def _flush_levels(self):
        """Send all pending levels as a single batched message."""
        try:
            if self._pending_levels:
                safe_broadcast("LEVEL", list(self._pending_levels.values()), type="level")
                self._pending_levels = {}
            self._level_timer_id = None
            return False
        except Exception as e:
            logger.log(f"Exception in _flush_levels: {e}", level='ERROR')
            self._level_timer_id = None
            return False

    @staticmethod
    def _db_to_percent(db):
        """Convert dB (-60..0) to percent (0..100)."""
        if db <= -60:
            return 0
        if db >= 0:
            return 100
        return int((db + 60) / 60 * 100)
