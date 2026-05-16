# Encoders

Outputs can share an encoder: when multiple outputs use the same encoder, the encoded stream is distributed without re-encoding. Outputs can also have their own dedicated encoder for different bitrates or profiles. Encoders are configured in `config.toml` and assigned to outputs.

## ⚠️ Bitrate Unit Gotcha — Read This First

Different GStreamer encoders take `bitrate` in **different units**. Setting `192` on an AAC encoder produces unusable garbage (it's 192 bits/second instead of 192 kbit/second).

| Encoder | `bitrate` unit | 192 kbit/s example | 4 Mbit/s example |
|---|---|---|---|
| `fdkaacenc` (AAC) | **bits/second** | `bitrate=192000` | n/a |
| `voaacenc` (AAC) | **bits/second** | `bitrate=192000` | n/a |
| `opusenc` (Opus) | **bits/second** | `bitrate=192000` | n/a |
| `lamemp3enc` (MP3) | **kbit/second** | `bitrate=192` | n/a |
| `avenc_mp2` (MP2) | **bits/second** | `bitrate=192000` | n/a |
| `x264enc` (H.264) | **kbit/second** | n/a | `bitrate=4000` |
| `x265enc` (H.265) | **kbit/second** | n/a | `bitrate=4000` |
| `vah264enc` (VAAPI) | **kbit/second** | n/a | `bitrate=4000` |
| `vulkanh264enc` (Vulkan) | **kbit/second** | n/a | `bitrate=4000` |
| `openh264enc` | **kbit/second** | n/a | `bitrate=4000` |
| `mpph264enc` (Rockchip) | **bits/second** | n/a | `bitrate=4000000` |

Symptom of getting AAC wrong: distorted/scratchy audio on SRT/RTMP outputs while the preview sounds fine. Symptom of getting H.264 wrong: massive 4-Gbit streams that nobody can ingest, or 4-bit slideshows.

## Configuration Syntax

Encoder options come as a single space-separated string of `key=value` pairs, passed verbatim to the GStreamer element:

```toml
[outputs.my_stream.video_encoder]
name    = "auto"           # or x264, vah264enc, vulkanh264enc, etc.
options = "bitrate=4000 pass=cbr speed-preset=veryfast key-int-max=60"
profile = "main"
```

`gst-inspect-1.0 <encoder>` on the host shows every property the encoder accepts.

## Encoder Reuse (Shared Encoders)

When multiple outputs need the same codec at the same bitrate, defining one encoder once and pointing many outputs at it cuts CPU/GPU usage proportionally — only ONE encode runs, the encoded bitstream fan-outs to every consumer.

### Named shared encoders

Declare encoders as standalone entities under `[encoders.<name>]`, then reference by name from each output's `video_encoder` / `audio_encoder` field:

```toml
# 1) Define the shared encoders
[encoders.h264_main]
type    = "video"
name    = "auto"
options = "bitrate=6000 pass=cbr speed-preset=veryfast key-int-max=60"

[encoders.aac_192]
type    = "audio"
name    = "aac"
options = "bitrate=192000"

# 2) Multiple outputs share them — encoded ONCE, sent to all
[outputs.srt_primary]
type          = "srtsink"
uri           = "srt://cdn-a.example.com:9999"
video_encoder = "h264_main"
audio_encoder = "aac_192"

[outputs.srt_backup]
type          = "srtsink"
uri           = "srt://cdn-b.example.com:9999"
video_encoder = "h264_main"     # same encode, second consumer
audio_encoder = "aac_192"
```

Use this whenever two outputs would otherwise encode the same source at the same bitrate (e.g. primary + backup CDN, SRT + RTMP simulcast at one rate).

### `@preview:program:<codec>` — piggyback on the preview encoder

DOVE always encodes the **program** output for WebRTC/HLS previews. Recording or archive outputs can hitch a ride on that encoder so the recording costs zero extra CPU:

```toml
[outputs.archive]
type          = "splitmuxsink"
location      = "rec-%Y%m%d-%H%M%S"
video_encoder = "@preview:program:h264"
audio_encoder = "@preview:program:aac"

[outputs.archive.mux]
name = "matroskamux"
```

The format is `@preview:program:<codec>` where `<codec>` is `h264`, `h265`, or `aac`. DOVE resolves it at startup to whatever encoder the program preview is using. The output inherits the preview's resolution and bitrate — you don't (and can't) override them.

**Use cases:** local recording, splitmuxsink archives, secondary HLS at the preview's bitrate. Anything that needs a DIFFERENT bitrate must use a named shared encoder (or its own dedicated encoder) instead.

### When NOT to share

- Outputs with different bitrate / resolution requirements (CDN at 6 Mbps + low-bandwidth backup at 1.5 Mbps) — must have separate encoders.
- Mixing H.264 and H.265 — different codecs, different encoders.
- Per-output audio filtering — audio filters live on the encoder, so shared encoders share filters. Outputs needing different audio processing (e.g. one with loudnorm, one without) need separate encoders.

## Auto Selection

Setting `video_encoder.name = "auto"` lets DOVE pick the best available encoder at startup. Priority order for H.264: `vah264enc` → `vah264lpenc` → `vaapih264enc` → `vulkanh264enc` → `openh264enc` → `x264enc`. VAAPI is preferred over Vulkan because the matching `vapostproc` element does color conversion and scaling on the GPU — no equivalent exists for the Vulkan path in GStreamer 1.28 yet.

## Available Encoder Types

### x264

Software H.264 encoder. Always available, broad client compatibility, the safe baseline. CPU-heavy at high resolutions.

**Key options**
- `bitrate=4000` — target rate in **kbit/s**.
- `pass=cbr|pass1|qual` — rate-control mode. `cbr` is required for most CDNs (Twitch, YouTube).
- `speed-preset=ultrafast|superfast|veryfast|faster|fast|medium|slow|slower|veryslow` — quality/CPU tradeoff. `veryfast` is the sweet spot for live.
- `key-int-max=60` — max GOP length. CDNs want a keyframe every 2 s, so set to `2 × framerate` (60 for 30 fps).
- `tune=zerolatency` — disables B-frames + lookahead for minimal latency. Required for SRT/WebRTC pipelines that target sub-second.

### openh264

Cisco's open-source H.264 encoder. Smaller binary footprint than `x264`, lower quality at the same bitrate. Useful as a software fallback when `x264` isn't desired (license caveats, etc.).

**Key options**
- `bitrate=4000` — target rate in **kbit/s**.
- `rate-control=quality|bitrate|buffer|timestamp` — `bitrate` is the live default.
- `complexity=low|medium|high` — CPU/quality tradeoff.

### vah264enc

VAAPI hardware H.264 encoder for AMD and Intel GPUs. Pairs with `vapostproc` for GPU-side scaling and color conversion — the most efficient hardware path on supported GPUs. ~5-10× less CPU than `x264enc` at the same bitrate.

**Key options**
- `bitrate=4000` — target rate in **kbit/s**.
- `rate-control=cbr|vbr|cqp` — Constant Bitrate / Variable / Constant QP.
- `key-int-max=60` — same as `x264`.
- `target-usage=1-7` — 1 = highest quality / most GPU work, 7 = fastest. Default 4.

**Requirements**
- `/dev/dri` must be passed into the container.
- For AMD: `docker-compose.amd.yml` overlay loads `RADV`.
- For Intel: `docker-compose.intel.yml` overlay loads `intel-media-driver`.
- Run `vainfo` inside the container to confirm hardware detection.

### vaapih264enc

Legacy VAAPI H.264 encoder. Use `vah264enc` instead unless your platform requires the older driver path. Same option names, same units.

### vulkanh264enc

Vulkan Video hardware H.264 encoder. Requires GStreamer 1.28+ and a Vulkan-capable GPU with video encode support (Mesa 26+). Alpine image only — not available in the Debian Trixie image.

**Key options**
- `bitrate=4000` — target rate in **kbit/s**.
- `key-int-max=60` — same as `x264`.

**Requirements**
- `/dev/dri` plus a Vulkan-capable driver: `mesa-vulkan-radv` (AMD), `mesa-vulkan-intel` (Intel).
- Run `vulkaninfo --summary` inside the container; look for `videoEncodeH264` feature support.

### mpph264enc

Rockchip Media Process Platform hardware encoder. Use on Rockchip-based SBCs/SoMs (RK3399, RK3588, etc.).

**Key options**
- `bitrate=4000000` — target rate in **bits/s** (note: different unit from `x264`/`vah264enc`!).
- `rc-mode=vbr|cbr` — rate-control mode.

**Requirements**
- Rockchip mpp library + kernel support on the host.
- Pass the appropriate `/dev/rga`, `/dev/mpp_service` devices into the container.

### x265

Software H.265 / HEVC encoder. Higher compression than H.264 at the cost of CPU. Use when downstream supports HEVC and bandwidth matters more than CPU.

**Key options**
- `bitrate=2500` — target rate in **kbit/s** (you can usually halve the H.264 rate for similar quality).
- `speed-preset=ultrafast|…|veryslow` — same scale as `x264`.
- `tune=zerolatency` — same as `x264`.

**Caveats**
- Many destinations (CDNs, browser playback) don't accept HEVC. Verify the receiver first.

## Auto Selection (Hardware Probing)

`auto` probes hardware encoders at startup by trying a READY transition. Failures are silent — the next encoder in the priority list is tried. The chosen encoder is logged at startup:

```
Auto-selected video encoder: vah264enc
```

## Audio Encoders

| Encoder | Container | Bitrate unit | Typical config |
|---|---|---|---|
| `fdkaacenc` (Fraunhofer FDK AAC) | mp4, ts, flv | **bits/s** | `bitrate=192000` |
| `voaacenc` (VisualOn AAC) | mp4, ts, flv | **bits/s** | `bitrate=128000` |
| `avenc_mp2` (MPEG-1 Layer 2) | mpegts | **bits/s** | `bitrate=192000 level=1` |
| `lamemp3enc` (LAME MP3) | mp3, mp4, ts | **kbit/s** | `bitrate=192` |
| `vorbisenc` (Vorbis) | webm, ogg | quality 0-10 | `quality=0.5` |
| `flacenc` (FLAC) | flac | lossless | — |
| `opusenc` (Opus) | webm, ogg | **bits/s** | `bitrate=128000 frame-size=20` |

**Pick by output:**
- SRT, RTMP, HLS, RTSP → `aac` (use `fdkaacenc`, never `<192000`)
- Icecast/Shoutcast → `mp3` (lamemp3enc, kbit/s) or AAC
- WebM (WebRTC, browser preview) → `opus`
- MPEG-TS broadcast-style → `mp2`

## Hardware Encoding Requirements

**VAAPI (AMD/Intel):** requires `/dev/dri` passed to the container.

**Vulkan:** requires a Vulkan-capable GPU with video encode support. Only available in the Alpine image.

**Rockchip:** requires the `mpp` runtime + relevant `/dev/*` device nodes.

**Docker Compose overrides:**
- `docker-compose.amd.yml` — AMD GPU (VAAPI + Vulkan RADV)
- `docker-compose.intel.yml` — Intel GPU (VAAPI + Vulkan ANV)
