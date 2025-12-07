# Audio Filters

Audio filters process audio in real-time on inputs, scene slots, and the program mixer. Filters can be added, removed, and reordered without interrupting playback.

## Filter Chain

Filters are applied in order between the volume control and the output.

**Signal flow:** Volume → [Filter 1] → [Filter 2] → … → Level Meter → Output

## Available Filters

### Dynamics

| Filter | Description | Parameters |
|--------|-------------|------------|
| **Compressor** | Reduces dynamic range | `threshold` (0–1), `ratio` (1–20), `characteristics` (soft-knee / hard-knee) |
| **Expander/Gate** | Expands dynamic range / noise gate | `threshold` (0–1), `ratio` (1–20) |
| **Limiter** | Hard limiter | — |
| **Gain** | Amplify or attenuate | `amplification` (0–4x) |

### EQ / Filter

| Filter | Description | Parameters |
|--------|-------------|------------|
| **High Pass** | Passes frequencies above cutoff | `cutoff` (20–2000 Hz), `poles` (2–8) |
| **Low Pass** | Passes frequencies below cutoff | `cutoff` (200–20000 Hz), `poles` (2–8) |
| **3-Band EQ** | Low / Mid / High bands | `band0`, `band1`, `band2` (-24 to +12 dB) |
| **10-Band EQ** | 31 Hz to 16 kHz | `band0`–`band9` (-24 to +12 dB) |

### Spatial

| Filter | Description | Parameters |
|--------|-------------|------------|
| **Pan** | Stereo L/R positioning | `panorama` (-1 left to +1 right) |
| **Phase Invert** | Inverts audio phase | `degree` (0–1) |

### Effects

| Filter | Description | Parameters |
|--------|-------------|------------|
| **Echo/Delay** | Audio echo with feedback | `delay` (1–1000 ms), `intensity` (0–1), `feedback` (0–0.9) |

## Using the UI

Click the waveform icon next to the volume slider on any input, scene slot, or program mixer to open the filter panel. From there:

- **Add** — click a filter type button at the bottom
- **Remove** — click the X on a filter card
- **Bypass** — click ON/BYP to toggle a filter without removing it
- **Reorder** — use the up/down arrows to change processing order
- **Adjust** — drag sliders to change parameters in real-time

## Configuration

Filters can be pre-configured in `config.toml` so they are applied at startup.

### Per-input filters

```toml
[inputs.mic]
type = "uridecodebin3"
uri  = "srt://mic.local:9000"
audio_filters = [
  { type = "highpass",    enabled = true, params = { cutoff = 80, poles = 4 } },
  { type = "compressor",  enabled = true, params = { threshold = 0.6, ratio = 4.0, characteristics = "soft-knee" } },
  { type = "eq3",         enabled = true, params = { band0 = -3, band1 = 0, band2 = 2 } },
]
```

### Per-slot filters (scene mixer)

Filters on scene slots are configured within the scene definition:

```toml
[scenes.main.cam]
xpos = 0
ypos = 0
audio_filters = [
  { type = "lowpass", enabled = true, params = { cutoff = 8000, poles = 4 } },
]
[scenes.main.cam.input]
type = "uridecodebin3"
uri  = "rtsp://camera.local/stream"
```

### Program mixer filters

```toml
[program]
audio_filters = [
  { type = "limiter", enabled = true, params = {} },
  { type = "amplify", enabled = true, params = { amplification = 1.2 } },
]
```

## API

Filters can be updated at runtime via the REST API or WebSocket:

```bash
# Add a lowpass filter to an input
curl -X PUT /api/inputs -H "Content-Type: application/json" \
  -d '{"uid": "INPUT_UID", "audio_filters": [
    {"type": "lowpass", "enabled": true, "params": {"cutoff": 4000, "poles": 4}}
  ]}'
```

Parameter changes on existing filters (same count and types) update in-place without interrupting audio. Structural changes (add, remove, reorder, toggle) briefly rebuild the filter chain.
