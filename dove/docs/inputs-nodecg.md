# NodeCG

The `nodecg` input embeds a [NodeCG](https://www.nodecg.dev/) bundle as a live video source. It uses `wpesrc` to render the NodeCG graphics page, with transparent background enabled for overlay use.

## What is NodeCG?

NodeCG is a broadcast graphics framework. Graphics are defined as bundles — web pages driven by a real-time data layer (NodeCG's replicants). NodeCG is commonly used in esports and live production for lower thirds, scoreboards, and animated overlays.

## Fields

| Field | Description |
|-------|-------------|
| Bundle URL | URL of the NodeCG bundle graphic (e.g. `http://nodecg:9090/bundles/my-bundle/graphics/overlay.html`) |

## Use Cases

- **Scoreboards** — updated live via NodeCG dashboard
- **Lower thirds** — animated name/title graphics
- **Animated overlays** — any NodeCG-driven visual

## Notes

- NodeCG must be running and accessible from the DOVE container (same Docker network or reachable host).
- This input is essentially a [wpesrc](inputs-wpesrc) input pointed at a NodeCG bundle URL. You can also use a plain `wpesrc` input for the same purpose if you prefer to specify the URL directly.

## Built-in Proxy

DOVE includes a reverse proxy for NodeCG. When configured, the NodeCG dashboard panels load through DOVE — same origin, same auth, no CORS issues. Both the HTTP routes and the NodeCG WebSocket are protected when auth is enabled.

### Setup

Add to `config.toml`:

```toml
[nodecg]
url = "http://nodecg:9090"
```

Or set the `NODECG_URL` environment variable.

### Docker Compose

Use the NodeCG overlay file:

```bash
docker compose -f docker-compose.yml -f docker-compose.nodecg.yml up
```

This adds a NodeCG service on the DOVE network and sets `NODECG_URL` automatically.

### How it works

The proxy mounts NodeCG paths at root level (`/bundles/`, `/dashboard/`, `/socket.io/`, etc.) so that NodeCG's root-relative URLs work in iframes. When [authentication](/help/auth) is enabled, the proxy requires the `user` role — users without `dove-user` group membership cannot access the NodeCG dashboard or its WebSocket.

The wpesrc rendering (video capture of graphics pages) goes directly over the Docker network and does not use the proxy.
