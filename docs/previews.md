# Previews

DOVE supports two preview delivery methods: **WebRTC** and **HLS**. Both can run simultaneously from the same encoder — no double-encoding.

## WebRTC (default)

- Ultra-low latency (~100ms)
- Uses WHEP protocol
- Requires UDP connectivity (or TURN relay for restrictive networks)
- Best for: live editing, real-time monitoring

## HLS (fallback)

- Higher latency (~3 seconds)
- Works through any HTTP reverse proxy
- No UDP or TURN needed — pure HTTPS
- Best for: restrictive networks, external monitoring, mobile

## Configuration

Preview types are configured per category in `config.toml`:

```toml
[preview.inputs]
type = ["webrtcbin", "hlssink2"]   # both WebRTC and HLS
width = 320
height = 160
video_encoder.name = "auto"

[preview.scenes]
type = ["webrtcbin"]               # WebRTC only
width = 640
height = 320

[preview.program]
type = ["webrtcbin", "hlssink2"]   # both
width = 640
height = 320
```

- `type` accepts a list or a single string
- `video_encoder.name` = `"auto"` picks the best available H.264 encoder
- The encoder is shared between WebRTC and HLS — no extra encoding cost

## HLS URL format

HLS streams are accessible at:

```
/preview/hls/{source_uid}/index.m3u8
```

This URL works with VLC, ffplay, or any HLS-compatible player. Segments are auto-cleaned (3 segments on disk at any time).

## Preview mode toggle

The header bar has a preview mode toggle with three options:

- **Auto** (default) — Uses WebRTC. If WebRTC fails, automatically falls back to HLS.
- **WebRTC** — Forces WebRTC for all previews. No fallback.
- **HLS** — Forces HLS for all previews. Useful on restrictive networks or when UDP is unavailable.

HLS mode requires `"hlssink2"` in the `type` list for the relevant preview category. If HLS is not configured, the toggle has no effect and WebRTC is used.

## FPS tuning

Preview framerate is configurable via `[preview] fps` in `config.toml`:

```toml
[preview]
fps = 15
```

- **Default:** inherits `main.default_framerate` (typically 25 or 30).
- **Runtime adjustment:** the server status popover (admin only) exposes a slider (1–60). Lower values reduce CPU/bandwidth at the cost of motion smoothness.
- **Runtime changes are ephemeral** — they apply until the next restart. To make a change permanent, edit `[preview] fps` in `config.toml`.
