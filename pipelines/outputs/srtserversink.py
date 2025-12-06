from urllib.parse import urlparse
from gi.repository import Gst
from event_loop_bridge import safe_broadcast
from pipelines.outputs.output import Output
from api.outputs.srtserversink import SrtserversinkOutputDTO


class SrtserversinkOutput(Output):
    data: SrtserversinkOutputDTO

    def _parse_caller_stats(self, caller):
        """Extract stats from a caller structure (GstStructure or string)."""
        if isinstance(caller, str):
            result = Gst.Structure.from_string(caller)
            caller = result[0] if result else None
        if not caller or not hasattr(caller, 'n_fields'):
            return None
        stats = {}
        for j in range(caller.n_fields()):
            fname = caller.nth_field_name(j)
            fval = caller.get_value(fname)
            if fname == "send-rate-mbps":
                stats["rate"] = fval
            elif fname == "rtt-ms":
                stats["rtt"] = fval
            elif fname == "packets-sent-lost":
                stats["lost"] = fval
            elif fname == "packets-sent":
                stats["sent"] = fval
        return stats

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

        num_callers = 0
        total_rate = 0
        total_rtt = 0
        total_lost = 0
        total_sent = 0

        if stats is not None:
            # GStreamer 1.28+: callers in a GValueArray field
            callers = stats.get_value("callers") if stats.has_field("callers") else None
            if callers is not None and isinstance(callers, list):
                for caller in callers:
                    cs = self._parse_caller_stats(caller)
                    if cs:
                        num_callers += 1
                        total_rate += cs.get("rate", 0)
                        total_rtt += cs.get("rtt", 0)
                        total_lost += cs.get("lost", 0)
                        total_sent += cs.get("sent", 0)
            else:
                # Fallback: older GStreamer with per-caller top-level fields
                for i in range(stats.n_fields()):
                    name = stats.nth_field_name(i)
                    val = stats.get_value(name)
                    if hasattr(val, 'n_fields'):
                        cs = self._parse_caller_stats(val)
                        if cs:
                            num_callers += 1
                            total_rate += cs.get("rate", 0)
                            total_rtt += cs.get("rtt", 0)
                            total_lost += cs.get("lost", 0)
                            total_sent += cs.get("sent", 0)

        if num_callers > 0:
            new_state = "PLAYING"
            avg_rtt = total_rtt / num_callers
            new_stats = {"viewers": num_callers, "bitrate_mbps": total_rate, "rtt_ms": avg_rtt, "packets_lost": total_lost, "packets_sent": total_sent}
            details = f"{num_callers} viewer{'s' if num_callers != 1 else ''} | {total_rate:.1f} Mbps | RTT {avg_rtt:.0f}ms | lost {total_lost}/{total_sent}"
        else:
            new_state = "LISTENING"
            new_stats = {"viewers": 0}
            details = "No viewers connected"

        if self.data.state != new_state or self.data.stats != new_stats or self.data.details != details:
            self.data.state = new_state
            self.data.stats = new_stats
            self.data.details = details
            safe_broadcast("UPDATE", self.data)

    def build_pipeline_str(self, dynamic=False) -> str:
        uid = self.data.uid

        streamid_str = f" streamid=\"{self.data.streamid}\"" if self.data.streamid else ""
        latency_str = f" latency={self.data.latency}" if self.data.latency else ""

        # Extract port from URI for localport property (uri alone doesn't bind)
        parsed = urlparse(self.data.uri)
        port = parsed.port or 7001
        localport_str = f" localport={port}"

        video_str = (
            f" {self.get_video_start(dynamic)} "
            f" {self.data.mux.element} {self.data.mux.options} name=mux_{uid} ! "
            f" srtserversink name=sink_{uid} uri={self.data.uri} mode=2{localport_str}{latency_str}{streamid_str} "
        )

        audio_str = (
            f" {self.get_audio_start(dynamic)} mux_{uid}. "
        )

        return video_str + audio_str
