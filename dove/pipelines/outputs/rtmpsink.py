from dove.event_loop_bridge import safe_broadcast
from dove.pipelines.outputs.output import Output
from dove.api.outputs.rtmpsink import rtmpsinkOutputDTO


class rtmpsinkOutput(Output):
    data: rtmpsinkOutputDTO

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

        video_str = (
            f" {self.get_video_start(dynamic)} "
            f" {self.data.mux.element} {self.data.mux.options} name=mux_{uid} ! "
            f" rtmpsink name=sink_{uid} location={self.data.uri} sync=false "
        )

        audio_str = (
            f" {self.get_audio_start(dynamic)} mux_{uid}. "
        )

        return video_str + audio_str
