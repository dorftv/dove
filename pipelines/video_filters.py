"""Video filter definitions for inputs.

Mirrors audio_filters.py architecture — identity anchors (vf_in/vf_out),
dynamic add/remove via pad blocking. Reuses shared create/rebuild/update
functions from audio_filters.py.
"""


# Filter type → GStreamer pipeline string builder
VIDEO_FILTER_MAP = {
    'balance': lambda uid, i, p: (
        f"videobalance name=vf_{uid}_{i}"
        f" brightness={p.get('brightness', 0)}"
        f" contrast={p.get('contrast', 1)}"
        f" saturation={p.get('saturation', 1)}"
        f" hue={p.get('hue', 0)}"
    ),
    'flip': lambda uid, i, p: f"videoflip name=vf_{uid}_{i} video-direction={p.get('direction', 0)}",
    'crop': lambda uid, i, p: (
        f"videocrop name=vf_{uid}_{i}"
        f" top={p.get('top', 0)} bottom={p.get('bottom', 0)}"
        f" left={p.get('left', 0)} right={p.get('right', 0)}"
    ),
    'coloreffects': lambda uid, i, p: f"coloreffects name=vf_{uid}_{i} preset={p.get('preset', 0)}",
    'blur': lambda uid, i, p: f"gaussianblur name=vf_{uid}_{i} sigma={p.get('sigma', 1.2)}",
    'chromakey': lambda uid, i, p: (
        f"alpha name=vf_{uid}_{i} method=green"
    ),
    'text': lambda uid, i, p: (
        f"textoverlay name=vf_{uid}_{i}"
        f" text=\"{p.get('text', '')}\""
        f" valignment={p.get('valignment', 'bottom')}"
        f" halignment={p.get('halignment', 'center')}"
        f" font-desc=\"{p.get('font', 'Sans 24')}\""
    ),
}

# Filter type → (element_factory, property_dict) for dynamic creation
VIDEO_FILTER_ELEMENT_MAP = {
    'balance': lambda p: ('videobalance', {
        'brightness': p.get('brightness', 0),
        'contrast': p.get('contrast', 1),
        'saturation': p.get('saturation', 1),
        'hue': p.get('hue', 0),
    }),
    'flip': lambda p: ('videoflip', {'video-direction': p.get('direction', 0)}),
    'crop': lambda p: ('videocrop', {
        'top': p.get('top', 0), 'bottom': p.get('bottom', 0),
        'left': p.get('left', 0), 'right': p.get('right', 0),
    }),
    'coloreffects': lambda p: ('coloreffects', {'preset': p.get('preset', 0)}),
    'blur': lambda p: ('gaussianblur', {'sigma': p.get('sigma', 1.2)}),
    'chromakey': lambda p: ('alpha', {'method': 1}),  # 1 = green
    'text': lambda p: ('textoverlay', {
        'text': p.get('text', ''),
        'valignment': p.get('valignment', 2),  # 2 = bottom
        'halignment': p.get('halignment', 0),  # 0 = center
    }),
}


def build_video_filter_str(uid, filters: list) -> str:
    """Build pipeline string with vf_in/vf_out identity anchors."""
    anchor_in = f"identity name=vf_in_{uid} silent=true"
    anchor_out = f"identity name=vf_out_{uid} silent=true"

    if not filters:
        return f"{anchor_in} ! {anchor_out}"
    parts = []
    for i, f in enumerate(filters):
        if not f.enabled:
            continue
        builder = VIDEO_FILTER_MAP.get(f.type)
        if builder:
            parts.append(builder(uid, i, f.params))
    if not parts:
        return f"{anchor_in} ! {anchor_out}"
    return (
        f"{anchor_in} ! "
        + " ! ".join(parts)
        + f" ! {anchor_out}"
    )
