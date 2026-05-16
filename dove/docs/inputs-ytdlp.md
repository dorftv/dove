# yt-dlp

The yt-dlp input uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to resolve a page URL to a direct stream URI, then plays it like a regular [Streams & Files](inputs-uridecodebin3) input.

## Supported Sites

yt-dlp supports hundreds of sites including:

- YouTube
- Twitch (live and VOD)
- Vimeo
- Twitter / X
- Many others — see the [yt-dlp supported sites list](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

## Fields

| Field | Description |
|-------|-------------|
| URL | The page URL (not a direct stream URL) |

## How It Works

1. DOVE passes the URL to yt-dlp at input creation time.
2. yt-dlp extracts the best available direct stream URL.
3. DOVE plays that direct URL as a stream.

## Notes

- The extraction runs once at startup. If the stream URL expires (common with YouTube), recreate the input to refresh it.
- Quality selection uses yt-dlp defaults (best available format). Custom format strings are not currently exposed in the UI.
- yt-dlp must be installed in the container (included by default in the Docker image).
- Some sites require cookies or authentication. This is not currently supported via the UI.
