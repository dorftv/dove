# Inputs

Inputs are media sources added to the DOVE pipeline. Each input produces a normalized video and audio stream that can be assigned to scene slots.

## Common Controls

| Control | Description |
|---------|-------------|
| Play / Pause | Start or pause playback |
| Volume | Adjust the input's audio level |
| Position | Seek to a point in the media (file-based sources only) |
| Loop | Restart playback automatically when the source ends |

## Input Types

| Type | Description | Details |
|------|-------------|---------|
| `uridecodebin3` | Local files and network streams | [Streams & Files](inputs-uridecodebin3) |
| `playlist` | Sequence of video clips and HTML pages | [Playlist](inputs-playlist) |
| `wpesrc` | Web page rendered as video | [HTML / Web](inputs-wpesrc) |
| `ytdlp` | YouTube, Twitch, and other sites via yt-dlp | [yt-dlp](inputs-ytdlp) |
| `nodecg` | NodeCG broadcast graphics | [NodeCG](inputs-nodecg) |
| `testsrc` | Test patterns and color bars | [Test Source](inputs-testsrc) |

## Adding an Input

Click the **+** button in the Inputs panel, select the input type, and fill in the required fields. The input starts immediately and appears in the inputs list.

## Assigning to a Scene

Drag an input to a scene slot, or use the slot's input selector dropdown. Adjust position, size, alpha, and volume in the scene slot properties.
