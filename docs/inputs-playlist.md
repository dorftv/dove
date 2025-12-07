# Playlist

The `playlist` input plays a sequence of video clips and HTML pages in order. When the last item finishes, it can loop back to the start or chain to another playlist.

## Playlist Format

Playlists are defined in JSON. Each item specifies a type and a source:

```json
[
  { "type": "video", "uri": "file:///media/intro.mp4" },
  { "type": "html",  "uri": "https://example.com/overlay.html", "duration": 10 },
  { "type": "video", "uri": "file:///media/outro.mp4" }
]
```

### Item Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `"video"` or `"html"` |
| `uri` | string | URI of the media file or web page |
| `duration` | number | Duration in seconds (required for `html` items) |

## Controls

| Control | Action |
|---------|--------|
| Next | Skip to the next clip immediately |
| Previous | Go back to the previous clip |
| Loop | Restart the playlist from the beginning after the last item |

## Chaining

A playlist can chain to another playlist when it finishes. Set the `next_playlist` field to the URI of the next playlist file. Useful for building complex sequences without a single large JSON file.

## Notes

- If a video clip fails to load, it is skipped and playback continues with the next item.
- HTML items require a `duration` — without it the playlist cannot advance.
- Loop applies to the entire playlist, not individual clips.
