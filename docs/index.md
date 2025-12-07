# DOVE — Help

DOVE is a live video mixing application. Media sources (**Inputs**) are composited into layouts (**Scenes**). A scene is cut to **Program**, which is sent to all active **Outputs**. Outputs can share encoders to avoid redundant encoding.

## Core Concepts

- [Interface](/help/interface) — panels, workflow, controls
- [Scenes](/help/scenes) — compositor layouts, slots, properties
- [Configuration](/help/config) — config file, pre-loading scenes/inputs/outputs at startup
- [Outputs](/help/outputs) — streaming destinations
- [Encoders](/help/encoders) — hardware and software encoder selection

## Inputs

- [All Inputs](/help/inputs) — overview and common controls
- [Streams & Files](/help/inputs-uridecodebin3) — local files, HTTP, SRT, RTMP, RTSP
- [Playlist](/help/inputs-playlist) — sequence of video clips and HTML pages
- [HTML / Web](/help/inputs-wpesrc) — web page rendered as video source
- [yt-dlp](/help/inputs-ytdlp) — YouTube, Twitch, and hundreds of other sites
- [NodeCG](/help/inputs-nodecg) — broadcast graphics via NodeCG
- [Test Source](/help/inputs-testsrc) — color bars and test patterns

## Audio

- [Audio Filters](/help/audio-filters) — per-input, per-slot, and program audio processing

## Reference

- [Previews](/help/previews) — HLS and WebRTC preview streams
- [Authentication](/help/auth) — OIDC login, roles, and protecting external services
- [Keyboard Shortcuts](/help/keyboard-shortcuts)
- [Connection Status](/help/connection-status)
- [Debugging](/help/debugging)
