# Video Filters

Video filters process video in real-time on inputs, scene slots, and the program mixer. Filters can be added, removed, and reordered without interrupting playback.

## Filter Chain

Filters are applied in order between the input decoder and the compositor.

**Signal flow:** Decode → Caps → [Filter 1] → [Filter 2] → ... → Tee → Output

## Available Filters

### Color

| Filter | Description | Parameters |
|--------|-------------|------------|
| **Color Balance** | Brightness, contrast, saturation, hue | `brightness` (-1 to 1), `contrast` (0–2), `saturation` (0–2), `hue` (-1 to 1) |
| **Color Effect** | Preset color grading | `preset` (None / Heat / Sepia / Xray / X-Pro / Yellowblue) |

### Transform

| Filter | Description | Parameters |
|--------|-------------|------------|
| **Flip / Rotate** | Flip or rotate video | `direction` (None / CW 90 / 180 / CCW 90 / H-Flip / V-Flip) |
| **Crop** | Crop edges | `top`, `bottom`, `left`, `right` (0–500 px) |

### Effects

| Filter | Description | Parameters |
|--------|-------------|------------|
| **Blur** | Gaussian blur | `sigma` (0.1–10) |

## Using the UI

Click the camera icon next to any input, scene slot, or program mixer to open the video filter panel. From there:

- **Add** — click a filter type button at the bottom
- **Remove** — click the X on a filter card
- **Bypass** — click ON/BYP to toggle a filter without removing it
- **Reorder** — use the up/down arrows to change processing order
- **Adjust** — drag sliders or select presets to change parameters in real-time

## Configuration

Filters can be pre-configured in `config.toml` so they are applied at startup.

### Per-input filters

```toml
[inputs.camera]
type = "uridecodebin3"
uri  = "rtsp://camera.local/stream"
video_filters = [
  { type = "balance", enabled = true, params = { brightness = 0.1, contrast = 1.2, saturation = 1.0, hue = 0 } },
  { type = "crop",    enabled = true, params = { top = 20, bottom = 20, left = 0, right = 0 } },
]
```

### Per-slot filters (scene mixer)

Filters on scene slots are configured within the scene definition:

```toml
[scenes.main.cam]
xpos = 0
ypos = 0
video_filters = [
  { type = "blur", enabled = true, params = { sigma = 3.0 } },
]
[scenes.main.cam.input]
type = "uridecodebin3"
uri  = "rtsp://camera.local/stream"
```

### Program mixer filters

```toml
[program]
video_filters = [
  { type = "balance", enabled = true, params = { contrast = 1.1, saturation = 0.9 } },
]
```

## API

Filters can be updated at runtime via the REST API or WebSocket:

```bash
# Add a color balance filter to an input
curl -X PUT /api/inputs -H "Content-Type: application/json" \
  -d '{"uid": "INPUT_UID", "video_filters": [
    {"type": "balance", "enabled": true, "params": {"brightness": 0, "contrast": 1.2, "saturation": 1.0, "hue": 0}}
  ]}'
```

Parameter changes on existing filters (same count and types) update in-place without interrupting video. Structural changes (add, remove, reorder, toggle) briefly rebuild the filter chain via pad blocking.

## Element Availability

Video filters depend on GStreamer elements that may not be available in all builds. DOVE checks element availability at startup — unavailable filters are hidden from the UI. Check `/api/config/elements` to see which elements are available.

| Filter | GStreamer Element |
|--------|-------------------|
| Color Balance | `videobalance` |
| Flip / Rotate | `videoflip` |
| Crop | `videocrop` |
| Color Effect | `coloreffects` |
| Blur | `gaussianblur` |
