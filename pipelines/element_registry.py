"""Element availability registry — probed once at startup.

Call probe_elements() before pipeline creation. All subsequent checks
use the cached result via is_available().
"""

from gi.repository import Gst
from logger import logger

_available = {}

# All GStreamer elements DOVE might use (excluding encoders — those use api/helper.py)
_ELEMENTS_TO_PROBE = [
    # Audio filters
    'audiocheblimit', 'equalizer-3bands', 'equalizer-10bands',
    'audiodynamic', 'rglimiter', 'audioamplify', 'audiopanorama',
    'audioinvert', 'audioecho',
    # Video filters
    'videobalance', 'coloreffects', 'videoflip', 'videocrop',
    'alpha', 'gaussianblur', 'textoverlay',
    # Core pipeline
    'compositor', 'audiomixer', 'audioconvert', 'videoconvert',
    'videoscale', 'videorate', 'audiorate', 'audioresample', 'vapostproc',
    'uridecodebin3', 'wpesrc', 'tee', 'queue',  # cefsrc: deprecated, re-add if needed
    'identity', 'capsfilter', 'level', 'volume',
    # Outputs
    'webrtcbin', 'proxysink', 'proxysrc',
    # Rust plugins (gst-plugins-rs) — optional
    'ebur128level', 'audioloudnorm', 'audiornnoise',
    'livesync', 'fallbackswitch', 'fallbacksrc',
    # LADSPA plugins — optional
    'ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-compressor-stereo',
    'ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-expander-stereo',
    'ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-gate-stereo',
    # frei0r video filters — optional
    'frei0r-filter-pixeliz0r', 'frei0r-filter-cartoon', 'frei0r-filter-glow',
    'frei0r-filter-vignette', 'frei0r-filter-film-grain', 'frei0r-filter-glitch0r',
    'frei0r-filter-scanline0r', 'frei0r-filter-sobel', 'frei0r-filter-colorhalftone',
]

# Map: filter type → required GStreamer element(s)
_AUDIO_FILTER_ELEMENTS = {
    'highpass': ['audiocheblimit'],
    'lowpass': ['audiocheblimit'],
    'eq3': ['equalizer-3bands'],
    'eq10': ['equalizer-10bands'],
    'compressor': ['ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-compressor-stereo'],
    'expander': ['ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-expander-stereo'],
    'gate': ['ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-gate-stereo'],
    'limiter': ['rglimiter'],
    'amplify': ['audioamplify'],
    'pan': ['audiopanorama'],
    'invert': ['audioinvert'],
    'echo': ['audioecho'],
    # Rust plugins (gst-plugins-rs audiofx) — optional
    'loudnorm': ['audioloudnorm'],
    'denoise': ['audiornnoise'],
}

_VIDEO_FILTER_ELEMENTS = {
    'balance': ['videobalance'],
    'flip': ['videoflip'],
    'crop': ['videocrop'],
    'coloreffects': ['coloreffects'],
    'blur': ['gaussianblur'],
    'chromakey': ['alpha'],
    'text': ['textoverlay'],
    'pixelate': ['frei0r-filter-pixeliz0r'],
    'cartoon': ['frei0r-filter-cartoon'],
    'glow': ['frei0r-filter-glow'],
    'vignette': ['frei0r-filter-vignette'],
    'grain': ['frei0r-filter-film-grain'],
    'glitch': ['frei0r-filter-glitch0r'],
    'scanlines': ['frei0r-filter-scanline0r'],
    'sobel': ['frei0r-filter-sobel'],
    'colorhalftone': ['frei0r-filter-colorhalftone'],
}


def probe_elements():
    """Probe all elements at startup. Call once before pipeline creation."""
    for name in _ELEMENTS_TO_PROBE:
        _available[name] = Gst.ElementFactory.find(name) is not None

    avail = [k for k, v in _available.items() if v]
    missing = [k for k, v in _available.items() if not v]
    if missing:
        logger.log(f"Element registry: {len(missing)} missing: {missing}", level='WARNING')
    logger.log(f"Element registry: {len(avail)}/{len(_available)} elements available", level='INFO')


def is_available(element_name):
    """Check if a GStreamer element was found at startup."""
    return _available.get(element_name, False)


def get_available_audio_filters():
    """Return list of audio filter type names that have all required elements."""
    return [ft for ft, elems in _AUDIO_FILTER_ELEMENTS.items()
            if all(_available.get(e, False) for e in elems)]


def get_available_video_filters():
    """Return list of video filter type names that have all required elements."""
    return [ft for ft, elems in _VIDEO_FILTER_ELEMENTS.items()
            if all(_available.get(e, False) for e in elems)]
