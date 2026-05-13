from dove.event_loop_bridge import safe_broadcast
from dove.pipelines.outputs.output import Output
from dove.api.outputs.srtsink import srtsinkOutputDTO


class srtsinkOutput(Output):
    data: srtsinkOutputDTO

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

        s = {}
        for i in range(stats.n_fields()):
            s[stats.nth_field_name(i)] = stats.get_value(stats.nth_field_name(i))

        bytes_sent = s.get("bytes-sent-total", 0)
        negotiated = s.get("negotiated-latency-ms", 0)

        if negotiated > 0 and bytes_sent > 0:
            new_state = "PLAYING"
            rtt = s.get("rtt-ms", 0)
            rate = s.get("send-rate-mbps", 0)
            lost = s.get("packets-sent-lost", 0)
            sent = s.get("packets-sent", 0)
            new_stats = {"bitrate_mbps": rate, "rtt_ms": rtt, "packets_lost": lost, "packets_sent": sent}
            details = f"{rate:.1f} Mbps | RTT {rtt:.0f}ms | lost {lost}/{sent}"
        elif bytes_sent == 0:
            new_state = "CONNECTING"
            new_stats = None
            details = "Waiting for SRT handshake"
        else:
            return

        if self.data.state != new_state or self.data.stats != new_stats or self.data.details != details:
            self.data.state = new_state
            self.data.stats = new_stats
            self.data.details = details
            safe_broadcast("UPDATE", self.data)

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid

        streamid_str = f" streamid=\"{self.data.streamid}\"" if self.data.streamid else ""
        video_str = (
            f" {self.get_video_start(dynamic)} "
            f" {self.data.mux.element} {self.data.mux.options} name=mux_{uid} ! "
            f" srtsink name=sink_{uid} uri={self.data.uri} latency={self.data.latency}{streamid_str} sync=false "
        )

        audio_str = (
            f" {self.get_audio_start(dynamic)} mux_{uid}. "
        )

        return video_str + audio_str
