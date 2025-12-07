from api.inputs.ytdlp import YtdlpInputDTO
from pipelines.inputs.uridecodebin3 import Uridecodebin3Input
from config_handler import ConfigReader
from logger import logger

import yt_dlp


class YtdlpInput(Uridecodebin3Input):
    data: YtdlpInputDTO

    def _get_source_uri(self):
        """Extract direct URL via yt-dlp before passing to uridecodebin3."""
        url = self.extract_video_url(self.data.uri)
        if not url:
            raise ValueError(f"Could not extract video URL from {self.data.uri}")
        return url

    def extract_video_url(self, url):
        height = ConfigReader().get_default_height()

        ydl_opts = {
            # Single combined stream preferred, fallback to best merged
            'format': f'best[height<={height}]/bestvideo[height<={height}]+bestaudio/best',
            'format_sort': [f'res:{height}', 'ext:mp4:m4a', 'proto:https'],
            'quiet': True,
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # yt-dlp resolves the best format — use requested_formats or direct url
                if 'requested_formats' in info:
                    # Merged: prefer the video format's manifest/url
                    for fmt in info['requested_formats']:
                        if fmt.get('vcodec') != 'none':
                            return fmt['url']

                if info.get('url'):
                    return info['url']

                # Fallback: scan formats for best combined
                formats = info.get('formats', [])
                for f in reversed(formats):
                    if f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                        return f['url']

                return None
        except yt_dlp.utils.DownloadError as e:
            logger.log(f"yt-dlp extraction failed for {url}: {e}", level='ERROR')
            return None
