from pathlib import Path
from typing import Optional
from uuid import UUID

from logger import logger
from event_loop_bridge import safe_broadcast

from pipelines.mixers.mixer import Mixer
from pipelines.audio_filters import build_audio_filter_str
from pipelines.video_filters import build_video_filter_str
from api.mixers_dtos import sceneMixerDTO, mixerInputDTO, mixerCutDTO, mixerSlotDTO
from config_handler import ConfigReader
from gi.repository import Gst, GLib


class sceneMixer(Mixer):
    data: sceneMixerDTO

    def build_pipeline_str(self) -> str:
        """Return pipeline string with mixer elements and output tees."""
        uid = self.data.uid
        caps_video = self.get_caps('video')
        caps_audio = self.get_caps('audio')
        fallback_pattern = ConfigReader().get_scene_fallback_pattern()

        # Fallback source for compositor (required for continuous output)
        video_filters = getattr(self.data, 'video_filters', None) or []
        vfilter_str = build_video_filter_str(uid, video_filters)
        video_str = (
            f" videotestsrc do-timestamp=true is-live=true pattern={fallback_pattern} name=fallback_video_{uid} ! {caps_video} ! "
            f" compositor name=videomixer_{uid} background=black latency=70000000 start-time-selection=first force-live=true ignore-inactive-pads=true "
            f" ! videorate skip-to-first=true ! videoconvert ! videoscale ! {caps_video} "
            f" ! {vfilter_str} ! {self.get_video_end()} "
        )

        # Fallback source for audiomixer
        # start-time-selection=first: use first buffer's timestamp, not wait for all inputs
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

        # Create initial slots based on data.n or existing sources
        n = self.data.n or 0
        existing = len(self.data.sources)
        for i in range(existing, n):
            self.add_slot()

        # Link any sources that were pre-configured in the DTO
        for i, source in enumerate(self.data.sources):
            if source.src and source.src != "None":
                try:
                    self.link_source(i, UUID(str(source.src)))
                    # Apply pad properties after linking
                    for av in ["audio", "video"]:
                        self.update_pad_from_sources(av, i)
                except Exception as e:
                    logger.log(f"Failed to link initial source at index {i}: {e}", level='ERROR')

    pass

    async def update(self, data):
        """Handle slot updates - link/unlink sources, update properties."""
        from event_loop_bridge import bridge
        from api.input_models import AudioFilterDTO, VideoFilterDTO
        logger.log(f"Scene {self.data.uid} update: {list(data.keys())}", level='DEBUG')

        # Handle mixer-level updates (not per-slot)
        if 'index' not in data:
            if 'name' in data:
                self.data.name = data['name']
                safe_broadcast("UPDATE", self.data)
                return
            if 'audio_filters' in data:
                new_filters = [AudioFilterDTO(**f) if isinstance(f, dict) else f for f in data['audio_filters']]
                self._update_mixer_audio_filter_params(new_filters)
            if 'video_filters' in data:
                new_filters = [VideoFilterDTO(**f) if isinstance(f, dict) else f for f in data['video_filters']]
                self._update_mixer_video_filter_params(new_filters)
            if 'audio_filters' in data or 'video_filters' in data:
                safe_broadcast("UPDATE", self.data)
                return

        index = data.get('index', None)
        if index is not None:
            src = data.get('src')

            # Handle source linking/unlinking (must run on GLib thread for GStreamer ops)
            if 'src' in data:
                if src and src != "None":
                    try:
                        src_uid = UUID(str(src))
                    except ValueError:
                        logger.log(f"scene update: invalid src UUID {src!r}", level='WARNING')
                        return
                    bridge.run_sync_in_glib(lambda: self.link_source(index, src_uid))
                else:
                    bridge.run_sync_in_glib(lambda: self.unlink_source(index))

            # Handle per-slot audio_filters update (GStreamer ops on GLib thread)
            if 'audio_filters' in data:
                slot_filters = [AudioFilterDTO(**f) if isinstance(f, dict) else f for f in data['audio_filters']]
                logger.log(f"Slot {index} audio filters: {len(slot_filters)}", level='DEBUG')
                bridge.run_sync_in_glib(lambda: self._update_slot_audio_filters(index, slot_filters))

            # Handle per-slot video_filters update (GStreamer ops on GLib thread)
            if 'video_filters' in data:
                slot_vf = [VideoFilterDTO(**f) if isinstance(f, dict) else f for f in data['video_filters']]
                logger.log(f"Slot {index} video filters: {len(slot_vf)}", level='DEBUG')
                bridge.run_sync_in_glib(lambda: self._update_slot_video_filters(index, slot_vf))

            # Update other pad properties (filters handled above, skip them here)
            other_props = {k: v for k, v in data.items() if k not in ['index', 'uid', 'src', 'audio_filters', 'video_filters']}
            if other_props:
                self.data.update_mixer_input(index, **other_props)
                def do_update_pads():
                    for av in ["audio", "video"]:
                        self.update_pad_from_sources(av, index)
                bridge.run_sync_in_glib(do_update_pads)

            safe_broadcast("UPDATE", self.data)
