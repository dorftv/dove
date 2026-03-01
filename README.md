# DOVE — DORFTV Online Video Editor

![DOVE Logo](assets/logo.png)

**License: Apache-2.0** · **Python 3.12+** · **GStreamer 1.26+**

A live video mixing application with a web-based interface. Mix inputs into scenes, cut scenes to program, and stream the output to one or more destinations.

Developed by and for [DORFTV](https://dorftv.at). Inspired by [bbc/brave](https://github.com/bbc/brave).

<!-- Screenshots coming soon -->

## Concept

```
Inputs → Scenes → Program → Outputs
```

**Inputs** — media sources: local files, network streams, web pages, yt-dlp URLs, cameras, test patterns.

**Scenes** — compositor layouts combining multiple inputs. Each scene has slots with per-slot position, size, z-order, alpha, and volume controls.

**Program** — the currently live scene, sent to all active outputs simultaneously. Cut or crossfade between scenes.

**Outputs** — streaming destinations (SRT, RTMP, HLS, WebRTC, Decklink, etc.). Multiple outputs can share an encoder; dedicated encoders per output are also possible.

## Features

### Inputs

| Type | Description |
|------|-------------|
| `uridecodebin3` | Local files and streams (HTTP, SRT, RTMP, RTSP) |
| `playlist` | Sequence of video clips and HTML pages |
| `wpesrc` | Web page rendered as video (HTML/CSS/JS overlays) |
| `ytdlp` | YouTube, Twitch, and hundreds of other sites via yt-dlp |
| `nodecg` | NodeCG broadcast graphics |
| `v4l2src` | Webcams and capture cards (V4L2) |
| `imagesrc` | Still images (PNG, JPEG, WebP, SVG) |
| `testsrc` | SMPTE color bars and test patterns |
| `whip` | Browser screen share or webcam via WebRTC (experimental) |

### Outputs

| Type | Description |
|------|-------------|
| `srtsink` | SRT push to a remote listener |
| `srtserversink` | SRT server mode (remotes connect to DOVE) |
| `rtmpsink` | RTMP push |
| `rtspclientsink` | RTSP push |
| `hlssink2` | HLS segments (also used for previews) |
| `splitmuxsink` | Segmented file recording |
| `decklink` | SDI/HDMI via Blackmagic Design card |
| `shout2send` | Icecast/Shoutcast audio stream |

### Encoders

Hardware-accelerated encoding via VAAPI (AMD/Intel) or Vulkan. Software fallback via x264/x265. Set `video_encoder.name = "auto"` to pick the best available encoder at startup.

| Encoder | Type |
|---------|------|
| `x264` | Software (always available) |
| `openh264` | Software alternative |
| `vah264enc` / `vaapih264enc` | VAAPI (AMD/Intel) |
| `vulkanh264enc` | Vulkan (Mesa 26+, GStreamer 1.28+) |
| `mpph264enc` | Rockchip hardware |

### Audio & Video Filters

Per-input dynamic filter chains, applied at runtime without pipeline restart.

**Audio:** highpass, lowpass, 3-band/10-band EQ, compressor (LSP), expander (LSP), gate (LSP), limiter, amplify, pan, invert, echo, denoise, loudnorm. See [`docs/audio-filters.md`](docs/audio-filters.md).

**Video:** color balance, flip/mirror, crop, color effects, blur, chroma key. **Experimental (requires `frei0r-plugins`):** pixelate, cartoon, glow, vignette, film grain, glitch, scanlines, sobel edge, color halftone. See [`docs/video-filters.md`](docs/video-filters.md).

### Previews

- **WebRTC** — sub-second latency preview in the browser. Seamless source switching without WebRTC teardown.
- **HLS** — works in restricted networks, through any reverse proxy over HTTPS.

### Keyboard Shortcuts

Full keyboard control for live production: scene selection (1–9), cut/crossfade (Enter), transition toggle (T), and more. Press `?` in the UI for the full list. See [`docs/keyboard-shortcuts.md`](docs/keyboard-shortcuts.md).

## Quick Start

### Docker Compose

```bash
git clone https://github.com/dorftv/dove.git && cd dove
cp config-example.toml config.toml
```

**Software rendering (no GPU):**
```bash
docker compose up
```

**AMD GPU (VAAPI + Vulkan):**
```bash
docker compose -f docker-compose.yml -f docker-compose.amd.yml up
```

**Intel GPU (VAAPI + Vulkan):**
```bash
docker compose -f docker-compose.yml -f docker-compose.intel.yml up
```

Open [http://localhost:5000](http://localhost:5000)

### Configuration

Copy `config-example.toml` to `config.toml` and edit as needed. See [`docs/config.md`](docs/config.md) for all options.

```toml
[main]
default_resolution = "HD720"    # QHD, FullHD, HD720, nHD, …
default_framerate = "30/1"
volume = 0.7

[preview.scenes]
type = ["webrtcbin", "hlssink2"]
video_encoder.name = "auto"
```

## Authentication

Optional OIDC authentication (Keycloak, Authentik, Authelia, etc.). Disabled by default — enable with:

```toml
[auth]
enabled = true
issuer = "https://auth.example.com/realms/dove"
client_id = "dove-app"
client_secret = "your-secret"
```

Four roles: User, Supervisor, Outputs, Admin. See [`docs/auth.md`](docs/auth.md) for setup, role details, API tokens, and nginx integration.

## Documentation

In-app help is available at `/help` after starting DOVE. All docs are in the [`docs/`](docs/) directory:

- [Interface overview](docs/interface.md)
- [Inputs](docs/inputs.md) — [uridecodebin3](docs/inputs-uridecodebin3.md), [playlist](docs/inputs-playlist.md), [wpesrc](docs/inputs-wpesrc.md), [ytdlp](docs/inputs-ytdlp.md), [nodecg](docs/inputs-nodecg.md), [testsrc](docs/inputs-testsrc.md)
- [Scenes](docs/scenes.md)
- [Outputs](docs/outputs.md) · [Encoders](docs/encoders.md)
- [Audio filters](docs/audio-filters.md) · [Video filters](docs/video-filters.md)
- [Previews](docs/previews.md)
- [Configuration](docs/config.md)
- [Authentication](docs/auth.md)
- [Debugging](docs/debugging.md)

## Tech Stack

- **GStreamer 1.26+** — single unified pipeline
- **FastAPI + uvicorn** — REST API and WebSocket
- **Nuxt 4** — web frontend
- **Python 3.12+**
- **yt-dlp** — stream URL extraction

## Development

**Backend:**
```bash
cd dove
poetry install
python main.py -c config.toml
```

**Frontend:**
```bash
cd dove-frontend
npm install
npm run dev   # http://localhost:3000
```

**GStreamer debug:**
```bash
GST_DEBUG=2 GST_DEBUG_DUMP_DOT_DIR=/tmp python main.py -c config.toml
```

## Contributing

Contributions are welcome! Please open an issue first to discuss larger changes. For bug reports, include the GStreamer version, config, and relevant logs.

## Notes

- `wpesrc` requires `--cap-add SYS_ADMIN` and `--security-opt apparmor=unconfined` (handled by the provided compose files)
- Decklink requires a supported Blackmagic Design card and the `decklink` GStreamer plugin
- WebRTC previews use `announced_ip` for the server's public IP — set in `config.toml` or via `ANNOUNCED_IP` env var

## License

[Apache License 2.0](LICENSE)
