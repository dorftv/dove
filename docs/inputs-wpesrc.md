# HTML / Web

Renders a web page (HTML, CSS, JavaScript) as a live video source. The rendered page is composited at full frame rate.

## Fields

| Field | Description |
|-------|-------------|
| URI | URL of the web page to render (`http://`, `https://`, or `file:///`) |
| Transparent background | If enabled, the page background is transparent — useful for overlays |

## Use Cases

- **Lower thirds** — animated HTML/CSS graphics positioned over video
- **Tickers and clocks** — live-updating text rendered as a video layer
- **Custom graphics** — any web-based visual driven by JavaScript
- **Dashboard embeds** — internal tools or monitoring pages as a video source

## Transparent Overlays

Enable the **transparent background** option to remove the default white/black background. This lets the web page act as a graphic overlay — position it in a scene slot above other inputs using `alpha` and `zorder`.

## Notes

- Included in the Docker image by default.
- Some browser APIs (camera, microphone, local storage) may not be available.
- JavaScript runs normally, including timers, fetch, and WebSockets.
- For NodeCG-driven graphics, see [NodeCG](inputs-nodecg).
