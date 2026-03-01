from datetime import datetime
from pathlib import Path

from gi.repository import Gst

from logger import logger
from pipelines.outputs.output import Output
from api.outputs.splitmuxsink import splitmuxsinkOutputDTO

MUX_EXTENSIONS = {
    "mpegtsmux": ".ts",
    "mp4mux": ".mp4",
    "matroskamux": ".mkv",
}

SEGMENT_DURATIONS = {
    "30m": 30 * 60,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
    "6h": 21600,
}


class splitmuxsinkOutput(Output):
    data: splitmuxsinkOutputDTO
    _full_duration_ns: int = 0
    _aligned: bool = False
    _use_fallback_dir: bool = False
    _fallback_dir: str = ""

    def _get_ext(self):
        return MUX_EXTENSIONS.get(self.data.mux.name, ".ts")

    def _probe_location_writable(self, location_template: str) -> bool:
        """Test whether the configured location directory is writable."""
        try:
            probe_name = datetime.now().strftime(location_template) + self._get_ext()
            parent = Path(probe_name).parent
            parent.mkdir(parents=True, exist_ok=True)
            test_file = parent / f".dove_probe_{self.data.uid}"
            test_file.write_text("")
            test_file.unlink()
            return True
        except Exception as e:
            logger.log(
                f"splitmuxsink {self.data.uid}: location '{location_template}' not writable ({e}), falling back to /var/dove/recordings/{self.data.uid}/",
                level='WARNING',
            )
            return False

    def _compute_initial_max_size_time(self):
        """Compute initial segment duration to align to clock boundary."""
        duration_s = SEGMENT_DURATIONS.get(self.data.segment_duration, 3600)
        self._full_duration_ns = duration_s * Gst.SECOND

        now = datetime.now()
        total_seconds = now.hour * 3600 + now.minute * 60 + now.second
        seconds_into_interval = total_seconds % duration_s
        seconds_until_boundary = duration_s - seconds_into_interval

        # If less than 60s until boundary, extend by one full interval
        if seconds_until_boundary < 60:
            seconds_until_boundary += duration_s

        self._aligned = False
        return seconds_until_boundary * Gst.SECOND

    def connect_signals(self, pipeline):
        sink = pipeline.get_by_name(f"mux_{self.data.uid}")
        if sink:
            sink.connect("format-location-full", self._on_format_location)
            logger.log(f"splitmuxsink {self.data.uid}: connected format-location-full signal", level='DEBUG')

    def _on_format_location(self, splitmux, fragment_id, first_sample):
        # After first segment, restore full duration
        if fragment_id >= 1 and not self._aligned:
            splitmux.set_property("max-size-time", self._full_duration_ns)
            self._aligned = True

        ext = self._get_ext()
        try:
            if self._use_fallback_dir:
                filename = str(Path(self._fallback_dir) / (datetime.now().strftime("recording_%Y-%m-%d_%H-%M-%S") + ext))
            else:
                filename = datetime.now().strftime(self.data.location) + ext
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.log(
                f"splitmuxsink {self.data.uid}: failed to resolve location ({e}), using fallback",
                level='WARNING',
            )
            Path(self._fallback_dir).mkdir(parents=True, exist_ok=True)
            filename = str(Path(self._fallback_dir) / (datetime.now().strftime("recording_%Y-%m-%d_%H-%M-%S") + ext))

        logger.log(f"splitmuxsink {self.data.uid}: segment {fragment_id} → {filename}", level='DEBUG')
        return filename

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid
        initial_max_size_time = self._compute_initial_max_size_time()

        # location is needed as fallback; format-location-full signal overrides it
        ext = self._get_ext()
        self._fallback_dir = f"/var/dove/recordings/{uid}"
        fallback_location = f"{self._fallback_dir}/segment%05d{ext}"
        Path(self._fallback_dir).mkdir(parents=True, exist_ok=True)

        # Probe the user-configured location once; if not writable, fall back for the whole session
        self._use_fallback_dir = not self._probe_location_writable(self.data.location)

        # Parse elements needed for caps negotiation with splitmuxsink
        # (splitmuxsink creates its internal muxer lazily, so caps must be
        # established by upstream parse elements)
        video_parse = "h264parse ! " if dynamic else ""
        audio_parse = "aacparse ! " if dynamic else ""

        video_str = (
            f" {self.get_video_start(dynamic)} "
            f" {video_parse}"
            f" splitmuxsink name=mux_{uid} "
            f" location={fallback_location} "
            f" max-size-time={initial_max_size_time} "
            f" muxer=\"{self.data.mux.element} {self.data.mux.options}\" "
        )

        audio_str = (
            f" {self.get_audio_start(dynamic)} {audio_parse}mux_{uid}.audio_0 "
        )

        return video_str + audio_str
