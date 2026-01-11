# Screencast (WHIP Ingest)

Share your browser screen or webcam as a DOVE input via WebRTC.

**Status:** Experimental

## How it works

1. Create a **Screencast** input from the input panel
2. Click **Share Screen** or **Share Camera** on the input card
3. Select what to share in the browser picker
4. The stream appears as a regular DOVE input — add it to scenes, mix it

## Technical details

Uses the [WHIP protocol](https://datatracker.ietf.org/doc/html/rfc9725) (WebRTC-HTTP Ingestion Protocol). The browser sends video via WebRTC to DOVE, which decodes and feeds it into the pipeline.

- **Video only** — audio is not captured (screen share rarely has system audio)
- **Codecs:** VP8, VP9, H264, AV1 (browser negotiates, DOVE auto-selects decoder)
- **Hardware decode:** VAAPI decoders preferred when available (AMD/Intel), software fallback
- **Resolution:** Configured per input (default 1280x720). Browser's native resolution is scaled to match

## Limitations

- One publisher per input (create multiple inputs for multiple shares)
- No audio capture from screen share
- Requires direct network path between browser and DOVE (no TURN support yet)
- Preview shows black until a publisher connects
