# Interface Overview

The DOVE interface is divided into four main areas: Inputs, Scenes, Program, and Outputs.

## Workflow

1. **Add inputs** — create media sources (files, streams, HTML, test patterns)
2. **Assign to scene slots** — drag or select inputs into scene compositor slots
3. **Preview the scene** — each scene shows a live preview before going live
4. **Cut to program** — press **Cut** or **Enter** to switch the live output
5. **Monitor outputs** — active outputs show their streaming status

## Panels

**Inputs** (left panel) — Lists all active media sources. Each input shows its type, status, and a live preview thumbnail. Controls include play/pause, volume, position, and loop. Click an input to expand its settings.

**Scenes** (center-top) — Compositor layouts. Each scene has one or more input slots. Assign inputs to slots and adjust position, size, alpha, and volume per slot. A scene can be previewed without being live.

**Program** (center) — The currently live scene being sent to all outputs. Shows the active scene name and a live preview. Use the **Cut** button or **Enter** key to switch to the selected scene.

**Outputs** (right panel) — Lists all configured streaming destinations. Each output shows its type and connection status. Outputs share the same encoder; starting one output starts the encoder for all.

## Common Controls

| Control | Action |
|---------|--------|
| Enter / Cut | Switch selected scene to program |
| Click scene | Select scene for preview |
| Volume slider | Adjust input or slot audio level |
| Loop toggle | Loop playback when source ends |
