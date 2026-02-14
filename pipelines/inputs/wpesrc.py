from api.inputs.wpesrc import WpesrcInputDTO
from .input import Input

import os

_USE_CEF = None  # Lazy init — Gst.init() not called at import time

def _check_cef():
    global _USE_CEF
    if _USE_CEF is None:
        # HTML_ENGINE env var or config: "auto" (default), "cefsrc", "wpesrc"
        engine = os.environ.get('HTML_ENGINE', 'auto')
        if engine == 'wpesrc':
            _USE_CEF = False
        elif engine == 'cefsrc':
            from gi.repository import Gst
            _USE_CEF = bool(Gst.ElementFactory.find("cefsrc"))
        else:  # auto
            from gi.repository import Gst
            _USE_CEF = bool(Gst.ElementFactory.find("cefsrc"))
    return _USE_CEF


class WpesrcInput(Input):
    data: WpesrcInputDTO

    def build_pipeline_str(self) -> str:
        """Return pipeline string fragment for this input."""
        uid = self.data.uid
        add_borders = "true" if getattr(self.data, 'fit', True) else "false"

        if _check_cef():
            url = self.data.location or ''
            video_str = (
                f' cefsrc url="{url}" do-timestamp=true name=cefsrc_{uid} ! '
                f"cefdemux name=cefdemux_{uid} "
                f"cefdemux_{uid}.video ! videoconvert ! videoscale name=videoscale_{uid} add-borders={add_borders} ! videorate skip-to-first=true ! "
                f"video/x-raw,width={self.data.width},height={self.data.height},format=BGRA ! "
                f"videoconvert ! {self.get_video_end()} "
            )
            audio_str = (
                f" cefdemux_{uid}.audio ! audioconvert ! audioresample ! "
                f"{self.get_caps('audio')} ! {self.get_audio_end()} "
            )
        else:
            self.data.has_audio = False
            video_str = (
                f' wpesrc location="{self.data.location or ""}" draw-background={self.data.draw_background} '
                f"name=wpesrc_{uid} ! videoconvert ! videoscale name=videoscale_{uid} add-borders={add_borders} ! videorate skip-to-first=true ! "
                f"video/x-raw,width={self.data.width},height={self.data.height},format=BGRA ! "
                f"videoconvert ! {self.get_video_end()} "
            )
            audio_str = ""
        return video_str + audio_str
