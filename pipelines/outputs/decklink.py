from event_loop_bridge import safe_broadcast
from pipelines.outputs.output import Output
from api.outputs.decklink import DecklinkOutputDTO


class DecklinkOutput(Output):
    data: DecklinkOutputDTO

    def check_stats(self):
        if not self._bin:
            return
        sink = self._bin.get_by_name(f"sink_{self.data.uid}")
        if not sink:
            return
        try:
            stats = sink.get_property("stats")
        except Exception:
            return
        if stats is None:
            return
        rate = stats.get_value("average-rate")
        dropped = stats.get_value("dropped")
        rendered = stats.get_value("rendered")
        new_stats = {"average_rate": rate, "dropped": dropped, "rendered": rendered}
        details = f"{rate:.1f} fps | rendered {rendered} | dropped {dropped}"
        if self.data.stats != new_stats or self.data.details != details:
            self.data.stats = new_stats
            self.data.details = details
            safe_broadcast("UPDATE", self.data)

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid

        interlace_str = "videoconvert ! interlace field-pattern=2:2 ! queue ! " if self.data.interlaced else ""

        video_str = (
            f" {self.get_video_start(dynamic)} "
            f" {interlace_str} videorate skip-to-first=true ! videoconvert ! videoscale ! "
            f" video/x-raw,format=UYVY ! queue ! "
            f" decklinkvideosink name=sink_{uid} device-number={self.data.device} mode={self.data.mode} sync=true "
        )

        audio_str = (
            f" {self.get_audio_start(dynamic)} "
            f" audioresample ! audioconvert ! queue ! "
            f" decklinkaudiosink device-number={self.data.device} sync=true "
        )

        return video_str + audio_str
