# Input Pickers (Proxies)

Configurable dropdowns in the "Add Input" dialog. Each `[proxy.<name>]` section declares a picker attached to a specific input type + field.

Defaults include `[proxy.v4l2]` (webcam device picker) and `[proxy.alsa]` (audio device picker). Other pickers must be configured in `config.toml`.

## Local Files & Images

Scan a directory tree for media. The picker shows everything matching the listed extensions.

```toml
[proxy.files]
type       = "uridecodebin3"
field      = "uri"
paths      = ["/videos"]
extensions = ["mp4", "mkv", "webm", "ts", "mp3", "flac"]

[proxy.images]
type       = "imagesrc"
field      = "location"
paths      = ["/images"]
extensions = ["png", "jpg", "webp"]
```

`paths` are scanned inside the container — mount your media directories via docker compose volumes. Omit a section entirely to hide it from the UI.

## OvenMediaEngine

Walks an [OvenMediaEngine](https://github.com/AirenSoft/OvenMediaEngine) origin's REST API (vhosts → apps → streams) and lists active streams. Each entry's URL is built from `url_template` with `{vhost}`, `{app}`, `{stream}` placeholders.

```toml
[proxy.ovenmedia]
type  = "uridecodebin3"
field = "uri"

[proxy.ovenmedia."dorftv-cdn"]
url          = "http://10.10.10.206:8081/v1"
url_template = "srt://10.10.10.206:9998?streamid={vhost}/{app}/{stream}/1080"
auth         = "admin:<token>"
```

Point `url` at the **origin** — edges only surface streams once a viewer connects. The template can express SRT, WebRTC, or LL-HLS — write the protocol and rendition suffix once; placeholders expand per stream.

For multiple OMEs, add additional `[proxy.ovenmedia."<name>"]` blocks. Each is queried independently.

## MediaMTX

Walks a [MediaMTX](https://github.com/bluenviron/mediamtx) server's path list. One picker entry per published path.

```toml
[proxy.mediamtx]
type  = "uridecodebin3"
field = "uri"

[proxy.mediamtx."live"]
url      = "http://mediamtx.example.com:9997/v3/paths/list"
base_url = "srt://mediamtx.example.com:1337"
user     = "read"
pass     = "<password>"
```

## Playlist Source

External URL that returns a JSON list of playlist entries. DOVE fetches and shows them in the picker.

```toml
[proxy.playlist]
type  = "playlist"
field = "next"
url   = "https://example.com/playlists.json?host=self"
```

## NodeCG Bundle

Pulls graphics bundle metadata from a [NodeCG](https://www.nodecg.dev/) instance. Used by the `nodecg` input type.

```toml
[proxy.nodecg]
url = "http://nodecg:9090"
```
