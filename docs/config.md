# Configuration

DOVE uses two TOML files. `config-default.toml` contains all defaults and is never edited. `config.toml` is your overrides file — only set what you want to change.

```bash
cp config-example.toml config.toml
```

## Main Settings

```toml
[main]
default_resolution = "HD720"   # QHD, FullHD, HD720, qHD, …
default_framerate  = "30/1"
volume             = 0.7       # default input volume
hls_path           = "/var/dove/hls"
recordings_path    = "/var/dove/recordings"
```

Available resolutions are defined in `[resolutions]` in `config-default.toml` (QHD 2560×1440 down to SmallPreview 320×180).

## Encoder

```toml
[video_encoder]
name = "auto"   # auto, x264, vah264enc, vulkanh264enc, …
```

`auto` probes hardware encoders at startup and falls back to x264. See [Encoders](/help/encoders).

## UI — Limit Available Types

Control which input and output types appear in the "+" menus:

```toml
[ui]
enabled_inputs  = ["uridecodebin3", "wpesrc", "ytdlp", "testsrc", "nodecg", "playlist"]
enabled_outputs = ["srtsink", "srtserversink", "rtmpsink", "hlssink2", "decklink"]
```

## Pre-loading Scenes, Inputs and Outputs

Entities defined in config are created automatically at startup — no manual clicking required. This is the main way to set up a fixed production layout.

### Defining Scenes

```toml
[scenes.main]
name = "Main"

[scenes.main.cam]
xpos  = 0
ypos  = 0
alpha = 1.0
[scenes.main.cam.input]
type = "uridecodebin3"
uri  = "rtsp://camera.local/stream"

[scenes.main.logo]
xpos   = 1720
ypos   = 40
width  = 160
height = 90
alpha  = 0.9
[scenes.main.logo.input]
type            = "wpesrc"
location        = "https://example.com/logo.html"
draw_background = false
```

Each `[scenes.<scene>.<slot>]` section defines a compositor slot. The nested `[…input]` table creates an input inline and assigns it to that slot.

### Reusing Inputs Across Scenes

Reference an input created in another slot by its `scene.slot` path:

```toml
[scenes.preview.topleft]
width  = 480
height = 270
input  = "main.cam"   # reuse the input from scenes.main.cam
```

### Standalone Inputs

Inputs that are not pre-assigned to a scene slot — they appear in the inputs list and can be dragged into slots manually:

```toml
[inputs.b_roll]
type = "uridecodebin3"
uri  = "file:///media/b-roll.mp4"
loop = true

[inputs.clock]
type            = "wpesrc"
location        = "https://example.com/clock.html"
draw_background = false
```

### Standalone Outputs

Outputs that start automatically at launch:

```toml
[outputs.stream]
type    = "srtsink"
host    = "srt.example.com"
port    = 9000

[outputs.backup]
type = "rtmpsink"
uri  = "rtmp://live.example.com/app/key"
```

## Locking

Prevent accidental changes in the UI:

```toml
[scenes.main]
locked     = true   # scene cannot be deleted
src_locked = true   # scene source (program cut) cannot be changed

[scenes.main.logo]
locked     = true   # slot cannot be removed
src_locked = true   # slot input cannot be reassigned
[scenes.main.logo.input]
locked = true       # input cannot be deleted
```

## WebRTC Preview

```toml
[webrtc]
announced_ip = "192.168.1.10"   # server's reachable IP for RTP
min_rtp_port = 10000
max_rtp_port = 10100
# stun_server = "stun://stun.example.com:3478"
```

`announced_ip` can also be set via the `ANNOUNCED_IP` environment variable.

See [Previews](/help/previews) for the full preview setup.
