# Streams & Files

Plays local media files and network streams. Supports a wide range of formats and URI schemes.

## Supported URI Schemes

| Scheme | Example |
|--------|---------|
| `file:///` | `file:///home/user/video.mp4` |
| `http://` / `https://` | `https://example.com/stream.mp4` |
| `srt://` | `srt://192.168.1.10:9000` |
| `rtmp://` | `rtmp://live.twitch.tv/app/streamkey` |
| `rtsp://` | `rtsp://camera.local/stream` |

## Fields

| Field | Description |
|-------|-------------|
| URI | The media URI to play |
| Loop | Restart from the beginning when the source ends (file sources only) |

## Notes

- **Live sources** (SRT, RTMP, RTSP): buffering is minimized for low latency. Loop has no effect on live sources.
- **File sources**: full seek and loop support. Position slider is active.
- **HTTP**: works for both file downloads and live streams. Latency depends on the server's chunking.
- Format support depends on the codecs available in the Docker image.
