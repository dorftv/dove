"""Shared audio filter definitions for inputs, mixers, and slots — types, element mapping, pipeline strings, and runtime params."""

import itertools
from gi.repository import Gst, GLib
from logger import logger

_rebuild_counter = itertools.count()


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
        f"audiodynamic mode=compressor name=af_{uid}_{i}"
        f" threshold={p.get('threshold', 1.0)} ratio={p.get('ratio', 1.0)}"
        f" characteristics={p.get('characteristics', 'soft-knee')}"
    ),
    'expander': lambda uid, i, p: (
        f"audiodynamic mode=expander name=af_{uid}_{i}"
        f" threshold={p.get('threshold', 1.0)} ratio={p.get('ratio', 1.0)}"
    ),
    'limiter': lambda uid, i, p: f"rglimiter name=af_{uid}_{i}",
    'amplify': lambda uid, i, p: f"audioamplify name=af_{uid}_{i} amplification={p.get('amplification', 1.0)}",
    'pan': lambda uid, i, p: f"audiopanorama name=af_{uid}_{i} panorama={p.get('panorama', 0.0)}",
    'invert': lambda uid, i, p: f"audioinvert name=af_{uid}_{i} degree={p.get('degree', 0.0)}",
    'echo': lambda uid, i, p: f"audioecho name=af_{uid}_{i} max-delay=1000000000 delay={int(p.get('delay', 250) * 1000000)} intensity={p.get('intensity', 0.5)} feedback={p.get('feedback', 0.0)}",
}

# Filter type → (element_factory, property_dict) for dynamic Gst.ElementFactory.make()
FILTER_ELEMENT_MAP = {
    'highpass': lambda p: ('audiocheblimit', {'mode': 1, 'cutoff': p.get('cutoff', 80), 'poles': p.get('poles', 4)}),
    'lowpass': lambda p: ('audiocheblimit', {'mode': 0, 'cutoff': p.get('cutoff', 8000), 'poles': p.get('poles', 4)}),
    'eq3': lambda p: ('equalizer-3bands', {f'band{n}': p.get(f'band{n}', 0) for n in range(3)}),
    'eq10': lambda p: ('equalizer-10bands', {f'band{n}': p.get(f'band{n}', 0) for n in range(10)}),
    'compressor': lambda p: ('audiodynamic', {'mode': 0, 'threshold': p.get('threshold', 1.0), 'ratio': p.get('ratio', 1.0)}),
    'expander': lambda p: ('audiodynamic', {'mode': 1, 'threshold': p.get('threshold', 1.0), 'ratio': p.get('ratio', 1.0)}),
    'limiter': lambda p: ('rglimiter', {}),
    'amplify': lambda p: ('audioamplify', {'amplification': p.get('amplification', 1.0)}),
    'pan': lambda p: ('audiopanorama', {'panorama': p.get('panorama', 0.0)}),
    'invert': lambda p: ('audioinvert', {'degree': p.get('degree', 0.0)}),
    'echo': lambda p: ('audioecho', {'max-delay': 1000000000, 'delay': int(p.get('delay', 250) * 1000000), 'intensity': p.get('intensity', 0.5), 'feedback': p.get('feedback', 0.0)}),
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
    return key, val


def create_filter_elements(uid, prefix, enabled_filters, pipeline, element_map=None, audio=True):
    """Create filter elements + scaffolding (audioconvert/F32LE for audio, identity for video).

    Returns (pre, caps_or_None, filter_elems, post) or None on failure.
    """
    gen = next(_rebuild_counter)
    emap = element_map or FILTER_ELEMENT_MAP

    if audio:
        pre = Gst.ElementFactory.make("audioconvert", f"{prefix}_pre_{uid}_{gen}")
        caps_elem = Gst.ElementFactory.make("capsfilter", f"{prefix}_caps_{uid}_{gen}")
        caps_elem.set_property("caps", Gst.Caps.from_string("audio/x-raw,format=F32LE"))
        post = Gst.ElementFactory.make("audioconvert", f"{prefix}_post_{uid}_{gen}")
    else:
        pre = Gst.ElementFactory.make("identity", f"{prefix}_pre_{uid}_{gen}")
        pre.set_property("silent", True)
        caps_elem = None
        post = Gst.ElementFactory.make("identity", f"{prefix}_post_{uid}_{gen}")
        post.set_property("silent", True)

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

    return pre, caps_elem, filter_elems, post


def link_filter_chain(pre, caps_elem, filter_elems, post):
    """Link a filter chain: pre → [caps] → [filters] → post.
    caps_elem may be None (video path — no format conversion needed).
    """
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


def update_filter_params(filters, find_element_fn, uid, anchor_in=None, anchor_out=None):
    """Update filter parameters in-place; walks the chain between anchors, skipping scaffolding."""
    anchor_in = anchor_in or f"af_in_{uid}"
    anchor_out = anchor_out or f"af_out_{uid}"
    af_in = find_element_fn(anchor_in)
    af_out = find_element_fn(anchor_out)
    if not af_in or not af_out:
        return

    # Collect filter elements between anchors (skip scaffolding)
    filter_elems = []
    pad = af_in.get_static_pad("src")
    current = pad.get_peer()
    while current:
        elem = current.get_parent()
        if elem == af_out:
            break
        factory = elem.get_factory()
        if factory and factory.get_name() not in ("audioconvert", "capsfilter", "identity"):
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


def rebuild_between_anchors(af_in, af_out, new_filters, uid, pipe, element_map=None, audio=True):
    """Rebuild filter chain between identity anchors via pad blocking. Works for audio/video/mixer chains."""
    in_src = af_in.get_static_pad("src")
    if not in_src:
        return False

    def _do_rebuild(pad, info, user_data):
        try:
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
                result = create_filter_elements(uid, prefix, enabled, pipe, emap, audio=audio)
                if result:
                    ac_pre, caps_elem, filter_elems, ac_post = result
                    in_src.link(ac_pre.get_static_pad("sink"))
                    link_filter_chain(ac_pre, caps_elem, filter_elems, ac_post)
                    link_result = ac_post.get_static_pad("src").link(out_sink)
                    logger.log(f"Filter chain rebuilt for {uid}: {len(filter_elems)} filters", level='INFO')
                else:
                    in_src.link(out_sink)
                    logger.log(f"Filter chain creation failed for {uid}, bypassed", level='WARNING')
            else:
                # No enabled filters — direct link
                link_result = in_src.link(out_sink)
                logger.log(f"Filter chain cleared for {uid}", level='INFO')

        except Exception as e:
            logger.log(f"Filter rebuild error for {uid}: {e}", level='ERROR')
            import traceback
            traceback.print_exc()
            try:
                in_src.link(af_out.get_static_pad("sink"))
            except Exception:
                pass

        return Gst.PadProbeReturn.REMOVE

    in_src.add_probe(Gst.PadProbeType.BLOCK_DOWNSTREAM, _do_rebuild, None)
    return False
