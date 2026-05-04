"""Shared audio filter definitions for inputs, mixers, slots, and encoders — types, element mapping, pipeline strings, and runtime params."""

import itertools
from gi.repository import Gst, GLib
from logger import logger

_rebuild_counter = itertools.count()

_LSP_COMPRESSOR = "ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-compressor-stereo"
_LSP_EXPANDER = "ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-expander-stereo"
_LSP_GATE = "ladspa-lsp-plugins-ladspa-so-http---lsp-plug-in-plugins-ladspa-gate-stereo"




# Filter type → GStreamer pipeline string builder (for Gst.parse_bin_from_description)
AUDIO_FILTER_MAP = {
    'highpass': lambda uid, i, p: f"audiocheblimit mode=high-pass name=af_{uid}_{i} cutoff={p.get('cutoff', 80)} poles={p.get('poles', 4)}",
    'lowpass': lambda uid, i, p: f"audiocheblimit mode=low-pass name=af_{uid}_{i} cutoff={p.get('cutoff', 8000)} poles={p.get('poles', 4)}",
    'eq3': lambda uid, i, p: (
        f"equalizer-3bands name=af_{uid}_{i}"
        + ''.join(f" band{n}={p.get(f'band{n}', 0)}" for n in range(3))
    ),
    'eq10': lambda uid, i, p: (
        f"equalizer-10bands name=af_{uid}_{i}"
        + ''.join(f" band{n}={p.get(f'band{n}', 0)}" for n in range(10))
    ),
    'compressor': lambda uid, i, p: (
        f"{_LSP_COMPRESSOR} name=af_{uid}_{i}"
        f" attack-threshold={p.get('attack_threshold', 0.12589)}"
        f" attack-time={p.get('attack_time', 20)}"
        f" release-threshold={p.get('release_threshold', 0)}"
        f" release-time={p.get('release_time', 150)}"
        f" ratio={p.get('ratio', 2.5)}"
        f" knee={p.get('knee', 0.5011957)}"
        f" makeup-gain={p.get('makeup_gain', 1.2589)}"
        f" compression-mode={p.get('compression_mode', 0)}"
        f" sidechain-mode={p.get('sidechain_mode', 1)}"
        f" sidechain-source={p.get('sidechain_source', 0)}"
        f" sidechain-type={p.get('sidechain_type', 0)}"
        f" sidechain-lookahead=0 sidechain-listen=false sidechain-preamp=1"
        f" stereo-split={'true' if p.get('stereo_split', False) else 'false'}"
        f" high-pass-filter-mode=0 low-pass-filter-mode=0"
    ),
    'expander': lambda uid, i, p: (
        f"{_LSP_EXPANDER} name=af_{uid}_{i}"
        f" expander-mode={p.get('expander_mode', 0)}"
        f" attack-threshold={p.get('attack_threshold', 0.01)}"
        f" attack-time={p.get('attack_time', 5)}"
        f" release-threshold={p.get('release_threshold', 0)}"
        f" release-time={p.get('release_time', 100)}"
        f" hold-time={p.get('hold_time', 0)}"
        f" ratio={p.get('ratio', 2.0)}"
        f" knee={p.get('knee', 0.5011957)}"
        f" makeup-gain={p.get('makeup_gain', 1.0)}"
        f" sidechain-mode={p.get('sidechain_mode', 0)}"
        f" sidechain-source={p.get('sidechain_source', 0)}"
        f" stereo-split={'true' if p.get('stereo_split', False) else 'false'}"
        f" sidechain-lookahead=0 sidechain-listen=false sidechain-preamp=1"
        f" high-pass-filter-mode=0 low-pass-filter-mode=0"
    ),
    'gate': lambda uid, i, p: (
        f"{_LSP_GATE} name=af_{uid}_{i}"
        f" curve-threshold={p.get('curve_threshold', 0.01)}"
        f" attack={p.get('attack', 10)}"
        f" release={p.get('release', 100)}"
        f" hold-time={p.get('hold_time', 50)}"
        f" reduction={p.get('reduction', 0)}"
        f" makeup-gain={p.get('makeup_gain', 1.0)}"
        f" sidechain-mode={p.get('sidechain_mode', 0)}"
        f" sidechain-source={p.get('sidechain_source', 0)}"
        f" stereo-split={'true' if p.get('stereo_split', False) else 'false'}"
        f" sidechain-lookahead=0 sidechain-listen=false sidechain-preamp=1"
        f" high-pass-filter-mode=0 low-pass-filter-mode=0"
    ),
    'limiter': lambda uid, i, p: f"rglimiter name=af_{uid}_{i}",
    'amplify': lambda uid, i, p: f"audioamplify name=af_{uid}_{i} amplification={p.get('amplification', 1.0)}",
    'pan': lambda uid, i, p: f"audiopanorama name=af_{uid}_{i} panorama={p.get('panorama', 0.0)}",
    'invert': lambda uid, i, p: f"audioinvert name=af_{uid}_{i} degree={p.get('degree', 0.0)}",
    'echo': lambda uid, i, p: f"audioecho name=af_{uid}_{i} max-delay=1000000000 delay={int(p.get('delay', 250) * 1000000)} intensity={p.get('intensity', 0.5)} feedback={p.get('feedback', 0.0)}",
    # gst-plugins-rs audiofx — RNNoise-based denoiser, ~10ms latency, safe for live chain
    'denoise': lambda uid, i, p: f"audiornnoise name=af_{uid}_{i} voice-activity-threshold={p.get('vad_threshold', 0.0)}",
    # Encoder-only (gst-plugins-rs audiofx) — 3s lookahead, unsuitable for live inputs/mixers
    'loudnorm': lambda uid, i, p: (
        f"audioloudnorm name=af_{uid}_{i}"
        f" loudness-target={p.get('target', -24.0)}"
        f" loudness-range-target={p.get('range', 7.0)}"
        f" max-true-peak={p.get('peak', -2.0)}"
        f" offset={p.get('offset', 0.0)}"
    ),
}

# Filter type → (element_factory, property_dict) for dynamic Gst.ElementFactory.make()
FILTER_ELEMENT_MAP = {
    'highpass': lambda p: ('audiocheblimit', {'mode': 1, 'cutoff': p.get('cutoff', 80), 'poles': p.get('poles', 4)}),
    'lowpass': lambda p: ('audiocheblimit', {'mode': 0, 'cutoff': p.get('cutoff', 8000), 'poles': p.get('poles', 4)}),
    'eq3': lambda p: ('equalizer-3bands', {f'band{n}': p.get(f'band{n}', 0) for n in range(3)}),
    'eq10': lambda p: ('equalizer-10bands', {f'band{n}': p.get(f'band{n}', 0) for n in range(10)}),
    'compressor': lambda p: (_LSP_COMPRESSOR, {
        'attack-threshold': p.get('attack_threshold', 0.12589),
        'attack-time': float(p.get('attack_time', 20)),
        'release-threshold': float(p.get('release_threshold', 0)),
        'release-time': float(p.get('release_time', 150)),
        'ratio': p.get('ratio', 2.5),
        'knee': p.get('knee', 0.5011957),
        'makeup-gain': p.get('makeup_gain', 1.2589),
        'compression-mode': p.get('compression_mode', 0),
        'sidechain-mode': p.get('sidechain_mode', 1),
        'sidechain-source': p.get('sidechain_source', 0),
        'sidechain-type': p.get('sidechain_type', 0),
        'sidechain-lookahead': 0.0,
        'sidechain-listen': False,
        'sidechain-preamp': 1.0,
        'stereo-split': p.get('stereo_split', False),
        'high-pass-filter-mode': 0,
        'low-pass-filter-mode': 0,
    }),
    'expander': lambda p: (_LSP_EXPANDER, {
        'expander-mode': p.get('expander_mode', 0),
        'attack-threshold': float(p.get('attack_threshold', 0.01)),
        'attack-time': float(p.get('attack_time', 5)),
        'release-threshold': float(p.get('release_threshold', 0)),
        'release-time': float(p.get('release_time', 100)),
        'hold-time': float(p.get('hold_time', 0)),
        'ratio': float(p.get('ratio', 2.0)),
        'knee': float(p.get('knee', 0.5011957)),
        'makeup-gain': float(p.get('makeup_gain', 1.0)),
        'sidechain-mode': p.get('sidechain_mode', 0),
        'sidechain-source': p.get('sidechain_source', 0),
        'stereo-split': p.get('stereo_split', False),
        'sidechain-lookahead': 0.0,
        'sidechain-listen': False,
        'sidechain-preamp': 1.0,
        'high-pass-filter-mode': 0,
        'low-pass-filter-mode': 0,
    }),
    'gate': lambda p: (_LSP_GATE, {
        'curve-threshold': float(p.get('curve_threshold', 0.01)),
        'attack': float(p.get('attack', 10)),
        'release': float(p.get('release', 100)),
        'hold-time': float(p.get('hold_time', 50)),
        'reduction': float(p.get('reduction', 0)),
        'makeup-gain': float(p.get('makeup_gain', 1.0)),
        'sidechain-mode': p.get('sidechain_mode', 0),
        'sidechain-source': p.get('sidechain_source', 0),
        'stereo-split': p.get('stereo_split', False),
        'sidechain-lookahead': 0.0,
        'sidechain-listen': False,
        'sidechain-preamp': 1.0,
        'high-pass-filter-mode': 0,
        'low-pass-filter-mode': 0,
    }),
    'limiter': lambda p: ('rglimiter', {}),
    'amplify': lambda p: ('audioamplify', {'amplification': p.get('amplification', 1.0)}),
    'pan': lambda p: ('audiopanorama', {'panorama': p.get('panorama', 0.0)}),
    'invert': lambda p: ('audioinvert', {'degree': p.get('degree', 0.0)}),
    'echo': lambda p: ('audioecho', {'max-delay': 1000000000, 'delay': int(p.get('delay', 250) * 1000000), 'intensity': p.get('intensity', 0.5), 'feedback': p.get('feedback', 0.0)}),
    'denoise': lambda p: ('audiornnoise', {'voice-activity-threshold': p.get('vad_threshold', 0.0)}),
    # Encoder-only
    'loudnorm': lambda p: ('audioloudnorm', {
        'loudness-target': p.get('target', -24.0),
        'loudness-range-target': p.get('range', 7.0),
        'max-true-peak': p.get('peak', -2.0),
        'offset': p.get('offset', 0.0),
    }),
}


def build_audio_filter_str(uid, filters: list) -> str:
    """Build pipeline string fragment for audio filters.

    Always includes identity anchors (af_in/af_out) for dynamic filter add/remove.
    When enabled filters exist, wraps them in audioconvert for F32LE format.
    """
    anchor_in = f"identity name=af_in_{uid} silent=true"
    anchor_out = f"identity name=af_out_{uid} silent=true"

    if not filters:
        return f"{anchor_in} ! {anchor_out}"
    parts = []
    for i, f in enumerate(filters):
        if not f.enabled:
            continue
        builder = AUDIO_FILTER_MAP.get(f.type)
        if builder:
            parts.append(builder(uid, i, f.params))
    if not parts:
        return f"{anchor_in} ! {anchor_out}"
    return (
        f"{anchor_in} ! "
        + " ! ".join(parts)
        + f" ! {anchor_out}"
    )


def transform_filter_param(filter_type, key, val):
    """Transform a filter parameter value for GStreamer set_property.

    Handles unit conversions (e.g., echo delay ms → ns) and
    skips read-only properties (e.g., max-delay).
    Returns (key, val) or None to skip the param.
    """
    if filter_type == 'echo':
        if key == 'delay':
            return key, int(val * 1000000)
        if key == 'max-delay':
            return None
    if filter_type == 'denoise':
        if key == 'vad_threshold':
            return 'voice-activity-threshold', val
    if filter_type in ('compressor', 'expander', 'gate',
                       'pixelate', 'cartoon', 'glow', 'vignette', 'grain',
                       'glitch', 'scanlines', 'sobel', 'colorhalftone'):
        return key.replace('_', '-'), val
    return key, val


def create_filter_elements(uid, prefix, enabled_filters, pipeline, element_map=None,
                            audio=True, allow_rate_conversion=False):
    """Create filter elements + scaffolding (audioconvert/F32LE for audio, identity for video).

    When `allow_rate_conversion` is True (encoder chains only), the single hardcoded
    F32LE capsfilter is replaced with per-filter audioconvert+audioresample wrappers
    in `link_filter_chain`, so filters with narrow caps (e.g. audioloudnorm requires
    192kHz F64LE) can negotiate their own format. A final audioconvert+audioresample
    + capsfilter(F32LE 48kHz) before `post` restores the pipeline format.

    Input/mixer/slot chains keep the simple single-caps behavior (no rate conversion
    wrappers) to avoid the flush-chain problems we hit earlier.

    Returns (pre, caps_or_None, filter_elems, post) or None on failure.
    """
    gen = next(_rebuild_counter)
    emap = element_map or FILTER_ELEMENT_MAP

    if audio:
        pre = Gst.ElementFactory.make("audioconvert", f"{prefix}_pre_{uid}_{gen}")
        caps_elem = Gst.ElementFactory.make("capsfilter", f"{prefix}_caps_{uid}_{gen}")
        if allow_rate_conversion:
            # Final caps lock the chain output back to pipeline format (48kHz F32LE)
            # — per-filter converters in link_filter_chain handle intermediate formats.
            caps_elem.set_property("caps", Gst.Caps.from_string("audio/x-raw,format=F32LE,rate=48000"))
        else:
            caps_elem.set_property("caps", Gst.Caps.from_string("audio/x-raw,format=F32LE"))
        post = Gst.ElementFactory.make("audioconvert", f"{prefix}_post_{uid}_{gen}")
    else:
        pre = Gst.ElementFactory.make("videoconvert", f"{prefix}_pre_{uid}_{gen}")
        caps_elem = None
        post = Gst.ElementFactory.make("videoconvert", f"{prefix}_post_{uid}_{gen}")

    if not pre or not post:
        logger.log(f"Failed to create filter scaffolding for {prefix}_{uid}", level='ERROR')
        return None

    pipeline.add(pre)
    if caps_elem:
        pipeline.add(caps_elem)
    pipeline.add(post)
    pre.set_state(Gst.State.PLAYING)
    if caps_elem:
        caps_elem.set_state(Gst.State.PLAYING)
    post.set_state(Gst.State.PLAYING)

    filter_elems = []
    for i, f in enumerate(enabled_filters):
        factory_fn = emap.get(f.type)
        if not factory_fn:
            logger.log(f"Unknown filter type: {f.type}", level='WARNING')
            continue
        factory_name, props = factory_fn(f.params)
        elem = Gst.ElementFactory.make(factory_name, f"{prefix}_{uid}_{i}_{gen}")
        if not elem:
            logger.log(f"Failed to create filter element {factory_name}", level='ERROR')
            continue
        for k, v in props.items():
            try:
                elem.set_property(k, v)
            except Exception as e:
                logger.log(f"Failed to set {k}={v} on {prefix}_{uid}_{i}: {e}", level='WARNING')
        pipeline.add(elem)
        elem.set_state(Gst.State.PLAYING)
        filter_elems.append(elem)

    # Flag the pre element so link_filter_chain knows whether to insert per-filter wrappers
    pre._dove_rate_conv = allow_rate_conversion and audio
    return pre, caps_elem, filter_elems, post


def _make_wrapper(pipeline, name):
    """Create audioconvert+audioresample pair for per-filter format negotiation."""
    conv = Gst.ElementFactory.make("audioconvert", f"{name}_conv")
    resamp = Gst.ElementFactory.make("audioresample", f"{name}_resamp")
    pipeline.add(conv)
    pipeline.add(resamp)
    conv.set_state(Gst.State.PLAYING)
    resamp.set_state(Gst.State.PLAYING)
    return conv, resamp


def link_filter_chain(pre, caps_elem, filter_elems, post):
    """Link a filter chain: pre → [caps] → [filters] → post.
    caps_elem may be None (video path — no format conversion needed).

    Encoder mode (pre._dove_rate_conv is True):
        pre → resamp → filter1 → [conv+resamp → filterN]* → conv+resamp → caps → post
        Per-filter wrappers let filters with narrow caps (audioloudnorm = 192kHz F64LE)
        negotiate their own format independently.
    """
    rate_conv = getattr(pre, '_dove_rate_conv', False)

    if rate_conv and filter_elems:
        _link_rate_conv_chain(pre, caps_elem, filter_elems, post)
        return

    # Simple (legacy) path for input/mixer/slot chains
    first = caps_elem or (filter_elems[0] if filter_elems else post)
    pre.get_static_pad("src").link(first.get_static_pad("sink"))
    if caps_elem and filter_elems:
        caps_elem.get_static_pad("src").link(filter_elems[0].get_static_pad("sink"))
    elif caps_elem and not filter_elems:
        caps_elem.get_static_pad("src").link(post.get_static_pad("sink"))
        return
    if filter_elems:
        for j in range(len(filter_elems) - 1):
            filter_elems[j].get_static_pad("src").link(filter_elems[j + 1].get_static_pad("sink"))
        filter_elems[-1].get_static_pad("src").link(post.get_static_pad("sink"))
    elif not caps_elem:
        # No caps, no filters — pre already linked to post above
        pass


def _link_rate_conv_chain(pre, caps_elem, filter_elems, post):
    """Link with per-filter audioconvert+audioresample wrappers for encoder chains."""
    pipeline = pre.get_parent()

    def link(a, b):
        a.get_static_pad("src").link(b.get_static_pad("sink"))

    # pre → resamp_in → filter1 (pre is audioconvert, needs resampler for rate changes)
    first = filter_elems[0]
    resamp_in = Gst.ElementFactory.make("audioresample", f"{first.get_name()}_in_resamp")
    pipeline.add(resamp_in)
    resamp_in.set_state(Gst.State.PLAYING)
    link(pre, resamp_in)
    link(resamp_in, first)

    # Between each pair of filters: audioconvert + audioresample
    for j in range(len(filter_elems) - 1):
        a, b = filter_elems[j], filter_elems[j + 1]
        conv, resamp = _make_wrapper(pipeline, f"{a.get_name()}_to_{b.get_name()}")
        link(a, conv)
        link(conv, resamp)
        link(resamp, b)

    # last filter → audioconvert+audioresample → caps(F32LE 48kHz) → post
    last = filter_elems[-1]
    conv_out, resamp_out = _make_wrapper(pipeline, f"{last.get_name()}_to_caps")
    link(last, conv_out)
    link(conv_out, resamp_out)
    link(resamp_out, caps_elem)
    link(caps_elem, post)


def update_filter_params(filters, find_element_fn, uid, anchor_in=None, anchor_out=None):
    """Update filter parameters in-place; walks the chain between anchors, skipping scaffolding."""
    anchor_in = anchor_in or f"af_in_{uid}"
    anchor_out = anchor_out or f"af_out_{uid}"
    af_in = find_element_fn(anchor_in)
    af_out = find_element_fn(anchor_out)
    if not af_in or not af_out:
        return

    # Collect filter elements between anchors (skip scaffolding)
    # Also skip audioresample and queue — used by encoder rate-conversion wrappers.
    filter_elems = []
    pad = af_in.get_static_pad("src")
    current = pad.get_peer()
    while current:
        elem = current.get_parent()
        if elem == af_out:
            break
        factory = elem.get_factory()
        if factory and factory.get_name() not in ("audioconvert", "audioresample", "capsfilter", "identity", "queue", "videoconvert", "videoscale"):
            filter_elems.append(elem)
        src = elem.get_static_pad("src")
        current = src.get_peer() if src else None

    # Apply params by position
    enabled = [f for f in filters if f.enabled]
    for i, f in enumerate(enabled):
        if i >= len(filter_elems):
            break
        elem = filter_elems[i]
        for key, val in f.params.items():
            result = transform_filter_param(f.type, key, val)
            if result is None:
                continue
            key, val = result
            try:
                elem.set_property(key, val)
            except Exception as e:
                logger.log(f"Failed to set {key}={val} on {elem.get_name()}: {e}", level='WARNING')


def rebuild_between_anchors(af_in, af_out, new_filters, uid, pipe, element_map=None, audio=True,
                             allow_rate_conversion=False):
    """Rebuild filter chain between identity anchors via pad blocking. Works for audio/video/mixer chains.

    allow_rate_conversion: encoder-only flag that enables per-filter audioconvert+audioresample
    wrappers, so loudnorm (192kHz F64LE) can coexist with other filters in the same chain.
    """
    in_src = af_in.get_static_pad("src")
    if not in_src:
        return False

    def _do_rebuild(pad, info, user_data):
        # double-block prevents half-built chain emitting partial buffers
        tail_block_pad = af_out.get_static_pad("sink").get_peer() if af_out.get_static_pad("sink") else None
        tail_probe_id = tail_block_pad.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, lambda *_: Gst.PadProbeReturn.OK, None) if tail_block_pad else 0
        try:
            _tail_gen = next(_rebuild_counter)
            out_sink = af_out.get_static_pad("sink")

            # Walk from af_in to af_out, collect elements between
            elems_to_remove = []
            current_pad = in_src.get_peer()
            while current_pad:
                elem = current_pad.get_parent()
                if elem == af_out:
                    break
                elems_to_remove.append(elem)
                src = elem.get_static_pad("src")
                current_pad = src.get_peer() if src else None

            # Unlink af_in from chain
            peer = in_src.get_peer()
            if peer:
                in_src.unlink(peer)

            # Unlink old elements
            for elem in elems_to_remove:
                src = elem.get_static_pad("src")
                if src:
                    p = src.get_peer()
                    if p:
                        src.unlink(p)

            # Defer remove+NULL to after probe completes and data resumes.
            # Removing from a Gst.Bin during pad probe causes EOS.
            # Removing from pipeline is safe but we unify the path.
            def _deferred_cleanup(elems=elems_to_remove, parent=pipe):
                for elem in elems:
                    elem.set_state(Gst.State.NULL)
                    if elem.get_parent() == parent:
                        parent.remove(elem)
                return False
            GLib.idle_add(_deferred_cleanup)

            # Build new filter chain
            enabled = [f for f in new_filters if f.enabled]
            emap = element_map or FILTER_ELEMENT_MAP

            if enabled:
                prefix = "af" if audio else "vf"
                result = create_filter_elements(uid, prefix, enabled, pipe, emap, audio=audio,
                                                 allow_rate_conversion=allow_rate_conversion)
                if result:
                    ac_pre, caps_elem, filter_elems, ac_post = result
                    in_src.link(ac_pre.get_static_pad("sink"))
                    link_filter_chain(ac_pre, caps_elem, filter_elems, ac_post)
                    if not audio:
                        # gaussianblur/alpha output AYUV, textoverlay emits GstVideoOverlayComposition;
                        # videoscale + BGRA capsfilter re-normalize to pipeline resolution.
                        caps_str = "video/x-raw,format=BGRA"
                        try:
                            current = pad.get_current_caps()
                            if current:
                                s = current.get_structure(0)
                                ok_w, wv = s.get_int("width")
                                ok_h, hv = s.get_int("height")
                                if ok_w and ok_h:
                                    caps_str += f",width={wv},height={hv}"
                        except Exception:
                            pass
                        prefix = "vf"
                        vscale = Gst.ElementFactory.make("videoscale", f"{prefix}_vscale_{uid}_{_tail_gen}")
                        vcaps = Gst.ElementFactory.make("capsfilter", f"{prefix}_vcaps_{uid}_{_tail_gen}")
                        vcaps.set_property("caps", Gst.Caps.from_string(caps_str))
                        pipe.add(vscale)
                        pipe.add(vcaps)
                        vscale.set_state(Gst.State.PLAYING)
                        vcaps.set_state(Gst.State.PLAYING)
                        ac_post.get_static_pad("src").link(vscale.get_static_pad("sink"))
                        vscale.get_static_pad("src").link(vcaps.get_static_pad("sink"))
                        vcaps.get_static_pad("src").link(out_sink)
                    else:
                        ac_post.get_static_pad("src").link(out_sink)
                    logger.log(f"Filter chain rebuilt for {uid}: {len(filter_elems)} filters", level='INFO')
                else:
                    in_src.link(out_sink)
                    logger.log(f"Filter chain creation failed for {uid}, bypassed", level='WARNING')
            else:
                # No enabled filters — direct link
                in_src.link(out_sink)
                logger.log(f"Filter chain cleared for {uid}", level='INFO')

        except Exception as e:
            logger.log(f"Filter rebuild error for {uid}: {e}", level='ERROR')
            import traceback
            logger.log(traceback.format_exc(), level='ERROR')
            try:
                in_src.link(af_out.get_static_pad("sink"))
            except Exception:
                pass

        if tail_block_pad and tail_probe_id:
            tail_block_pad.remove_probe(tail_probe_id)
        return Gst.PadProbeReturn.REMOVE

    in_src.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, _do_rebuild, None)
    return False
