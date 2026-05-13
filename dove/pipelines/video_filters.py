"""Video filter definitions — mirrors audio_filters.py (vf_in/vf_out anchors, shared create/rebuild/update)."""


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
    # frei0r video effects
    'pixelate': lambda uid, i, p: (
        f"frei0r-filter-pixeliz0r name=vf_{uid}_{i}"
        f" block-width={p.get('block_width', 0.022)}"
        f" block-height={p.get('block_height', 0.029)}"
    ),
    'cartoon': lambda uid, i, p: (
        f"frei0r-filter-cartoon name=vf_{uid}_{i}"
        f" triplevel={p.get('triplevel', 1.0)}"
        f" diffspace={p.get('diffspace', 0.004)}"
    ),
    'glow': lambda uid, i, p: (
        f"frei0r-filter-glow name=vf_{uid}_{i}"
        f" blur={p.get('blur', 0.5)}"
    ),
    'vignette': lambda uid, i, p: (
        f"frei0r-filter-vignette name=vf_{uid}_{i}"
        f" aspect={p.get('aspect', 0.5)}"
        f" clearcenter={p.get('clearcenter', 0.0)}"
        f" soft={p.get('soft', 0.6)}"
    ),
    'grain': lambda uid, i, p: (
        f"frei0r-filter-film-grain name=vf_{uid}_{i}"
        f" grain-amount={p.get('grain_amount', 0.1)}"
        f" red-grain={p.get('red_grain', 0.75)}"
        f" green-grain={p.get('green_grain', 1.0)}"
        f" blue-grain={p.get('blue_grain', 0.5)}"
        f" blur-amount={p.get('blur_amount', 0.5)}"
        f" dust-amount={p.get('dust_amount', 0.0)}"
        f" flicker={p.get('flicker', 0.0)}"
    ),
    'glitch': lambda uid, i, p: (
        f"frei0r-filter-glitch0r name=vf_{uid}_{i}"
        f" glitch-frequency={p.get('glitch_frequency', 0.5)}"
        f" block-height={p.get('block_height', 0.5)}"
        f" shift-intensity={p.get('shift_intensity', 0.5)}"
        f" color-glitching-intensity={p.get('color_glitching_intensity', 0.5)}"
    ),
    'scanlines': lambda uid, i, p: f"frei0r-filter-scanline0r name=vf_{uid}_{i}",
    'sobel': lambda uid, i, p: f"frei0r-filter-sobel name=vf_{uid}_{i}",
    'colorhalftone': lambda uid, i, p: (
        f"frei0r-filter-colorhalftone name=vf_{uid}_{i}"
        f" dot-radius={p.get('dot_radius', 0.4)}"
        f" cyan-angle={p.get('cyan_angle', 0.3)}"
        f" magenta-angle={p.get('magenta_angle', 0.45)}"
        f" yellow-angle={p.get('yellow_angle', 0.25)}"
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
    # frei0r video effects
    'pixelate': lambda p: ('frei0r-filter-pixeliz0r', {
        'block-width': float(p.get('block_width', 0.022)),
        'block-height': float(p.get('block_height', 0.029)),
    }),
    'cartoon': lambda p: ('frei0r-filter-cartoon', {
        'triplevel': float(p.get('triplevel', 1.0)),
        'diffspace': float(p.get('diffspace', 0.004)),
    }),
    'glow': lambda p: ('frei0r-filter-glow', {
        'blur': float(p.get('blur', 0.5)),
    }),
    'vignette': lambda p: ('frei0r-filter-vignette', {
        'aspect': float(p.get('aspect', 0.5)),
        'clearcenter': float(p.get('clearcenter', 0.0)),
        'soft': float(p.get('soft', 0.6)),
    }),
    'grain': lambda p: ('frei0r-filter-film-grain', {
        'grain-amount': float(p.get('grain_amount', 0.1)),
        'red-grain': float(p.get('red_grain', 0.75)),
        'green-grain': float(p.get('green_grain', 1.0)),
        'blue-grain': float(p.get('blue_grain', 0.5)),
        'blur-amount': float(p.get('blur_amount', 0.5)),
        'dust-amount': float(p.get('dust_amount', 0.0)),
        'flicker': float(p.get('flicker', 0.0)),
    }),
    'glitch': lambda p: ('frei0r-filter-glitch0r', {
        'glitch-frequency': float(p.get('glitch_frequency', 0.5)),
        'block-height': float(p.get('block_height', 0.5)),
        'shift-intensity': float(p.get('shift_intensity', 0.5)),
        'color-glitching-intensity': float(p.get('color_glitching_intensity', 0.5)),
    }),
    'scanlines': lambda p: ('frei0r-filter-scanline0r', {}),
    'sobel': lambda p: ('frei0r-filter-sobel', {}),
    'colorhalftone': lambda p: ('frei0r-filter-colorhalftone', {
        'dot-radius': float(p.get('dot_radius', 0.4)),
        'cyan-angle': float(p.get('cyan_angle', 0.3)),
        'magenta-angle': float(p.get('magenta_angle', 0.45)),
        'yellow-angle': float(p.get('yellow_angle', 0.25)),
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
