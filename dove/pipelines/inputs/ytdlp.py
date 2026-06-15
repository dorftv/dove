from dove.api.inputs.ytdlp import YtdlpInputDTO
from dove.pipelines.inputs.uridecodebin3 import Uridecodebin3Input
from dove.logger import logger

import yt_dlp


def _extract_ytdlp_url(url: str, height: int) -> str:
    """Resolve a yt-dlp-supported page URL to a direct media URL.

    Blocking network call. MUST be invoked via asyncio.to_thread from the
    async API handler — never from the GLib main thread.
    Raises yt_dlp.utils.* on failure (do not swallow).
    """
    ydl_opts = {
        'format': f'best[height<={height}]/bestvideo[height<={height}]+bestaudio/best',
        'format_sort': [f'res:{height}', 'vcodec:h264', 'ext:mp4:m4a', 'proto:https'],
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 20,
        'retries': 1,
        'fragment_retries': 1,
        'extractor_retries': 1,
        'cachedir': False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        if 'requested_formats' in info:
            for fmt in info['requested_formats']:
                if fmt.get('vcodec') != 'none':
                    return fmt['url']

        if info.get('url'):
            return info['url']

        formats = info.get('formats', [])
        for f in reversed(formats):
            if f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                return f['url']

        raise yt_dlp.utils.ExtractorError(f"No playable format found for {url}")


class YtdlpInput(Uridecodebin3Input):
    data: YtdlpInputDTO
    _resolved_uri: str | None = None

    def _get_source_uri(self):
        """Return the resolved direct URL set by the async route handler."""
        if not self._resolved_uri:
            raise RuntimeError(
                f"YtdlpInput {self.data.uid}: _resolved_uri not set; "
                "route handler must resolve before add_pipeline"
            )
        return self._resolved_uri
