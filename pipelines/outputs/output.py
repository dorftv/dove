from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from gi.repository import Gst

from api.output_models import OutputDTO
from pipelines.base import GSTBase


class Output(GSTBase, ABC):
    data: OutputDTO
    _bin: Optional[Gst.Bin] = None  # For dynamic addition
    _tee_pads: Optional[dict] = None  # Track tee pads for cleanup

    def get_video_start(self, dynamic=False) -> str:
        if dynamic:
            return f" queue name=video_queue_{self.data.uid} ! "
        # Non-dynamic: connect to encoder tee if encoder entity UUID is set
        if isinstance(self.data.video_encoder, UUID):
            return f" enc_tee_{self.data.video_encoder}. ! queue ! "
        tee_name = self._get_source_tee_name("video")
        return f" {tee_name}. ! queue ! "

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

    def attach(self, pipeline: Gst.Pipeline):
        """Clear stale references after initial pipeline build."""
        self._bin = None
        self._tee_pads = None
        self.connect_signals(pipeline)

    def connect_signals(self, pipeline: Gst.Pipeline):
        """Override in subclasses that need signal connections after pipeline build."""
        pass

    def check_stats(self):
        """Override in subclasses that have stats. Called every 1s from tick."""
        pass
