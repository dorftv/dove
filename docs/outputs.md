# Outputs

Outputs are streaming destinations that receive the program signal. Multiple outputs can share the same encoder — when they do, the encoded stream is distributed without re-encoding. Outputs can also have their own dedicated encoder if different bitrates or profiles are needed.

See [Encoders](encoders) for encoder selection and configuration.

## Output Types

| Type | Description |
|------|-------------|
| SRT Push | Connect to a remote SRT listener |
| SRT Server | Remote peers connect to DOVE |
| RTMP | Push to a streaming server (Nginx, Wowza, etc.) |
| RTSP | Push to an RTSP server |
| HLS | Segments written to disk, served via HTTP |
| Recording (`splitmuxsink`) | Segmented file recording to disk (configurable mux) |
| Decklink | SDI/HDMI output via a Blackmagic Design capture card |
| Icecast | Icecast/Shoutcast audio stream |

## Adding an Output

Use the **+** button in the Outputs panel. Select the output type and fill in the required fields (URI, host, port, etc.). The output starts encoding and streaming immediately after creation.

## Notes

- HLS and WebRTC are also used internally for preview streams — see [Previews](previews).
- Decklink requires a supported Blackmagic Design card and drivers.
- Icecast delivers audio only (no video).
