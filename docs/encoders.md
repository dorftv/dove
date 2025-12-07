# Encoders

Outputs can share an encoder: when multiple outputs use the same encoder, the encoded stream is distributed without re-encoding. Outputs can also have their own dedicated encoder for different bitrates or profiles. Encoders are configured in `config.toml` and assigned to outputs.

## Available Encoder Types

| Name | Type | Notes |
|------|------|-------|
| `x264` | Software | Always available, good compatibility |
| `openh264` | Software | Alternative software encoder |
| `vah264enc` | VAAPI hardware | AMD and Intel GPUs |
| `vaapih264enc` | VAAPI hardware | Legacy VAAPI path |
| `vulkanh264enc` | Vulkan hardware | Requires GStreamer 1.28+ (Alpine image only, not available in Debian Trixie) |
| `mpph264enc` | Hardware | Rockchip platforms |
| `x265` | Software | H.265/HEVC, higher compression |

## Auto Selection

Setting `video_encoder.name = "auto"` in `config.toml` lets DOVE pick the best available encoder at startup. It probes hardware encoders first and falls back to software (`x264`) if none are available.

## Configuration

In `config.toml`:

```toml
[video_encoder]
name = "auto"   # or: x264, vah264enc, vulkanh264enc, etc.
```

## Hardware Encoding Requirements

**VAAPI (AMD/Intel):** requires `/dev/dri` passed to the container.

**Vulkan:** requires a Vulkan-capable GPU with video encode support. Only available in the Alpine image.

**Docker Compose:** use the appropriate compose override file:
- `docker-compose.amd.yml` — AMD GPU (VAAPI + Vulkan RADV)
- `docker-compose.intel.yml` — Intel GPU (VAAPI + Vulkan ANV)
