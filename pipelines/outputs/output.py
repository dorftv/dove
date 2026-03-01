from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from gi.repository import Gst

from api.output_models import OutputDTO
from logger import logger
from pipelines.audio_filters import FILTER_LATENCY_MS
from pipelines.base import GSTBase


class Output(GSTBase, ABC):
    data: OutputDTO
    _bin: Optional[Gst.Bin] = None  # For dynamic addition
    _tee_pads: Optional[dict] = None  # Track tee pads for cleanup
    _video_delay_identity: Optional[Gst.Element] = None

    def get_video_start(self, dynamic=False) -> str:
        uid = self.data.uid
        if dynamic:
            return f" queue name=video_queue_{uid} ! identity name=video_delay_{uid} silent=true ts-offset=0 ! "
        # Non-dynamic: connect to encoder tee if encoder entity UUID is set
        if isinstance(self.data.video_encoder, UUID):
            return f" enc_tee_{self.data.video_encoder}. ! queue ! identity name=video_delay_{uid} silent=true ts-offset=0 ! "
        tee_name = self._get_source_tee_name("video")
        return f" {tee_name}. ! queue ! identity name=video_delay_{uid} silent=true ts-offset=0 ! "

    def get_audio_start(self, dynamic=False):
        if dynamic:
            return f" queue name=audio_queue_{self.data.uid} ! "
        if isinstance(self.data.audio_encoder, UUID):
            return f" enc_tee_{self.data.audio_encoder}. ! queue ! "
        tee_name = self._get_source_tee_name("audio")
        return f" {tee_name}. ! queue ! "

    def _get_source_tee_name(self, audio_or_video):
        """Determine tee name based on source type (input vs mixer)."""
        from pipeline_handler import HandlerSingleton
        from logger import logger
        handler = HandlerSingleton()

        # Check if source is a mixer
        mixer = handler.get_pipeline("mixers", self.data.src)
        if mixer:
            tee_name = f"scene_{audio_or_video}_tee_{self.data.src}"
            logger.log(f"Output {self.data.uid} connecting to mixer tee: {tee_name}", level='DEBUG')
            return tee_name

        # Otherwise it's an input
        tee_name = f"{audio_or_video}_tee_{self.data.src}"
        logger.log(f"Output {self.data.uid} connecting to input tee: {tee_name}", level='DEBUG')
        return tee_name

    # For single-pipeline architecture
    @abstractmethod
    def build_pipeline_str(self, dynamic=False) -> str:
        """Return pipeline string fragment for this output. Override in subclasses.

        Args:
            dynamic: If True, use named queues for ghost pads instead of tee references.
        """
        pass

    def get_video_delay_ns(self):
        """Compute delay needed to match audio encoder filter latency. Returns ns."""
        if getattr(self.data, 'is_preview', False):
            return 0
        ae_ref = getattr(self.data, 'audio_encoder', None)
        if not ae_ref:
            return 0
        from pipeline_handler import HandlerSingleton
        handler = HandlerSingleton()
        encoder = handler.get_pipeline('encoders', ae_ref)
        if not encoder:
            return 0
        max_lat_ms = 0
        for f in (getattr(encoder.data, 'audio_filters', None) or []):
            if f.enabled:
                max_lat_ms = max(max_lat_ms, FILTER_LATENCY_MS.get(f.type, 0))
        return max_lat_ms * 1_000_000

    def _update_video_delay(self):
        """Patch identity ts-offset to match audio filter latency. GLib thread only."""
        if not self._video_delay_identity:
            return
        delay_ns = self.get_video_delay_ns()
        current = self._video_delay_identity.get_property('ts-offset')
        if current != delay_ns:
            self._video_delay_identity.set_property('ts-offset', delay_ns)
            logger.log(f"Output {self.data.uid} video delay: {current // 1_000_000}ms -> {delay_ns // 1_000_000}ms", level='INFO')

    def attach(self, pipeline: Gst.Pipeline):
        """Clear stale references after initial pipeline build."""
        self._bin = None
        self._tee_pads = None
        self._video_delay_identity = pipeline.get_by_name(f"video_delay_{self.data.uid}")
        self.connect_signals(pipeline)

    def connect_signals(self, pipeline: Gst.Pipeline):
        """Override in subclasses that need signal connections after pipeline build."""
        pass

    def check_stats(self):
        """Override in subclasses that have stats. Called every 1s from tick."""
        pass
