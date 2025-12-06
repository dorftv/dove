from pydantic import BaseModel
from api.output_models import OutputDTO

from config_handler import ConfigReader
config = ConfigReader()


class GSTBase(BaseModel):
    """Base class for all pipeline components (inputs, outputs, mixers, encoders).

    In the single-pipeline architecture, components provide pipeline string
    fragments via build_pipeline_str() or bins via build_bin().
    """

    def describe(self):
        return self.data

    def get_caps(self, audio_or_video, format=None):
        """Generate GStreamer caps string for audio or video."""
        if audio_or_video == "audio":
            if format is None:
                format = config.get_default_audio_format()
            caps = f"audio/x-raw,format={format},layout=interleaved,rate={config.get_default_audio_rate()},channels={config.get_default_audio_channels()}"
        elif audio_or_video == "video":
            if format is None:
                format = "BGRA"
            caps = f"video/x-raw,format={format}"
            if self.data.width is not None:
                caps += f",width={self.data.width}"
            if self.data.height is not None:
                caps += f",height={self.data.height}"
            if issubclass(self.data.__class__, OutputDTO):
                if self.data.framerate is not None:
                    caps += f",framerate={self.data.framerate}"
        return caps

    def get_pipeline(self):
        """Return queryable element for position/duration. Override in subclasses."""
        return None

    class Config:
        arbitrary_types_allowed = True
