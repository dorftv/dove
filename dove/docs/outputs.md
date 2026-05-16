# Outputs

Outputs are streaming destinations that receive the program signal. Multiple outputs can share the same encoder — when they do, the encoded stream is distributed without re-encoding. Outputs can also have their own dedicated encoder if different bitrates or profiles are needed.

See [Encoders](encoders) for encoder selection and configuration — and **watch the bitrate-unit gotcha** documented there (AAC bitrate is in bits/s, H.264 bitrate is in kbit/s).

## Output Types

### srtsink

Push to a remote SRT listener (caller mode). The downstream side runs the listener; DOVE initiates the connection.

**Fields**
- **URI** *(required)* — `srt://host:port` of the remote listener.
- **Stream ID** *(optional)* — passed as the SRT `streamid` parameter. Used by listeners like OvenMediaEngine, MediaMTX, srtrelay to route per-stream.
- **Latency** *(optional, default 300 ms)* — receiver-side buffer for retransmission. Higher = more resilience to loss + jitter, more end-to-end delay. Typical: 120 ms (LAN), 300–800 ms (internet), 2000 ms (lossy long-haul).

**Example**
```toml
[outputs.cdn_push]
type     = "srtsink"
name     = "To CDN"
uri      = "srt://ingest.example.com:9999"
streamid = "live/show/1080"
latency  = 300

[outputs.cdn_push.video_encoder]
name    = "auto"
options = "bitrate=6000 speed-preset=veryfast pass=cbr"   # bitrate kbit/s for H.264

[outputs.cdn_push.audio_encoder]
name    = "aac"
options = "bitrate=192000"   # bits/s — see Encoders doc
```

**Gotchas**
- For AES encryption on the wire, add `?passphrase=…` to the URI (also requires the listener to expect it).
- `streamid` must match the listener's routing expectation exactly — character mismatch silently drops the connection.

### srtserversink

DOVE acts as the SRT listener; remote peers (caller-mode pulls) connect in. Useful for "give them the URL, they connect" workflows.

**Fields**
- **URI** *(required)* — listening interface + port, e.g. `srt://0.0.0.0:7777`.
- **Stream ID** *(optional)* — restricts which `streamid` callers may use. Empty = any.
- **Latency** *(optional, default 400 ms)* — see `srtsink` notes.

**Example**
```toml
[outputs.broadcast_pull]
type    = "srtserversink"
name    = "Broadcast Pull"
uri     = "srt://0.0.0.0:7777?mode=listener"
latency = 400
```

**Gotchas**
- Expose the UDP port in `docker-compose.yml` (`7777:7777/udp` by default).
- The container's `ANNOUNCED_IP` doesn't apply here — clients reach DOVE directly via this port.

### rtmpsink

RTMP push to a streaming server: [Nginx-RTMP](https://github.com/arut/nginx-rtmp-module), [Wowza](https://www.wowza.com/), [OvenMediaEngine](https://github.com/AirenSoft/OvenMediaEngine), [MediaMTX](https://github.com/bluenviron/mediamtx), YouTube Live, Twitch, etc.

**Fields**
- **URI** *(required)* — `rtmp://server:port/app/streamkey` (single URL with embedded path + key).

**Example**
```toml
[outputs.twitch_push]
type = "rtmpsink"
name = "Twitch"
uri  = "rtmp://live.twitch.tv/app/live_XXXXX_streamkey"

[outputs.twitch_push.video_encoder]
name    = "auto"
options = "bitrate=6000 pass=cbr speed-preset=veryfast key-int-max=60"

[outputs.twitch_push.audio_encoder]
name    = "aac"
options = "bitrate=160000"   # bits/s
```

**Gotchas**
- RTMP wants **H.264 video + AAC audio**. Other codec combos fail at the muxer.
- Most CDNs require a **keyframe every 2 seconds** — pin `key-int-max=2*framerate` on the H.264 encoder.
- Twitch/YouTube reject high bitrates without VBV — `pass=cbr` is the safe default.

### rtspclientsink

RTSP push to an RTSP server (typically [MediaMTX](https://github.com/bluenviron/mediamtx)).

**Fields**
- **Location** *(required)* — `rtsp://server:port/path`.

**Example**
```toml
[outputs.mediamtx_push]
type     = "rtspclientsink"
name     = "MediaMTX"
location = "rtsp://mediamtx.local:8554/live"
```

**Gotchas**
- Some RTSP servers require basic auth in the URL: `rtsp://user:pass@server:port/path`.
- Codec compatibility varies — H.264/AAC is the safe baseline.

### hlssink2

HLS segments written to disk and served over HTTP. Also used internally for HLS previews — see [Previews](previews).

Files are written under the `hls_path` configured in `[main]` (default `/var/dove/hls`). Mount that path as a volume to serve segments from a sibling nginx/Caddy container.

**Example**
```toml
[outputs.live_hls]
type = "hlssink2"
name = "Live HLS"

[outputs.live_hls.video_encoder]
name    = "auto"
options = "bitrate=4000"
```

**Gotchas**
- Disk I/O — segments rotate every few seconds. Use a tmpfs or fast SSD if you have many concurrent outputs.
- The included nginx in many setups serves from `hls_path` directly; CORS headers must be set on the front-end web server.

### splitmuxsink

Segmented file recording to disk. Configurable mux (mp4, mkv, ts, etc.) and per-segment duration / size.

**Fields**
- **Location** *(required)* — file-path pattern with `strftime` placeholders. Extension is added automatically based on the mux. Example: `recording-%Y%m%d-%H%M%S` → `recording-20260116-143027.mp4`.
- **Segment Duration** *(default `1h`)* — `1h`, `30m`, `5m`, etc. First segment aligns to the clock boundary so files land on the hour/minute.
- **Mux** *(optional)* — defaults to `mp4`; choose `mkv`, `mpegts`, `webm`, etc. via the encoder/mux selector.

**Example**
```toml
[outputs.archive]
type             = "splitmuxsink"
name             = "Archive"
location         = "recording-%Y%m%d-%H%M%S"
segment_duration = "30m"

[outputs.archive.mux]
name = "matroskamux"   # crash-safe; use mp4mux only if you accept loss on crash

[outputs.archive.video_encoder]
name    = "auto"
options = "bitrate=8000"
```

**Gotchas**
- The directory must exist and be writable by the `dove` user inside the container (`recordings_path` in `[main]`).
- `mp4` does NOT survive a crash mid-segment — the moov atom is written at finalize. Use `mkv` or `mpegts` for crash-safe recording.
- Set the segment duration carefully — too short = many files; too long = a crash loses everything since the last segment boundary.

### decklink

SDI/HDMI output via a [Blackmagic Design](https://www.blackmagicdesign.com/products/decklink) DeckLink capture card.

**Fields**
- **Device** *(required)* — DeckLink device index (`0`, `1`, …). `/dev/blackmagic*` or `decklink-info` lists installed devices.
- **Mode** *(required)* — Blackmagic mode ID for the desired resolution/framerate (e.g. `43` for 1080p25). See `decklink-info` output for the full list.
- **Interlaces** *(optional, default false)* — enable for interlaced modes.

**Example**
```toml
[outputs.studio_feed]
type       = "decklink"
name       = "Studio Feed"
device     = 0
mode       = 43       # 1080p25
interlaces = false
```

**Gotchas**
- Requires the card on the host and the `decklink` GStreamer plugin in the image.
- Pass `/dev/blackmagic*` into the container.
- Resolution/framerate from the mode MUST match DOVE's `default_resolution` / `default_framerate` exactly — mismatch causes negotiation failure or a black output.

### shout2send

[Icecast](https://icecast.org/) / Shoutcast audio stream. Audio only — no video.

**Fields**
- **IP** *(required)* — Icecast server hostname/IP.
- **Port** *(required)* — usually `8000`.
- **Mountpoint** *(required)* — e.g. `/stream.mp3`.
- **User** *(required)* — Icecast source username (often `source`).
- **Password** *(required)* — Icecast source password.

**Example**
```toml
[outputs.radio]
type       = "shout2send"
name       = "Radio"
ip         = "icecast.example.com"
port       = 8000
mount      = "/live.mp3"
user       = "source"
password   = "..."

[outputs.radio.audio_encoder]
name    = "mp3"
options = "bitrate=192"   # mp3 — kbit/s
```

**Gotchas**
- `mp3` and `aac` encoders take **different bitrate units** — see the [Encoders](encoders) bitrate gotcha section.
- The mountpoint extension should match the mux: `.mp3` for mp3, `.aac` for AAC, `.ogg` for Vorbis.

## Adding an Output

Use the **+** button in the Outputs panel. Select the output type and fill in the required fields. The output starts encoding and streaming immediately after creation.

## Notes

- HLS and WebRTC are also used internally for preview streams — see [Previews](previews).
- Decklink requires a supported Blackmagic Design card and drivers.
- Icecast delivers audio only (no video).
