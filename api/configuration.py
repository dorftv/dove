import os
import toml
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from api.helper import get_encoder_types
from api.auth import require_role, require_read, is_auth_enabled, get_current_user
from gi.repository import Gst, GLib

from config_handler import ConfigReader
config = ConfigReader()

router = APIRouter(prefix="/api")


@router.get("/healthz")
async def healthz(request: Request):
    handler = request.app.state.pipeline_handler
    if not handler or not handler.core_pipeline or not handler.core_pipeline.pipeline:
        return JSONResponse({"status": "starting"}, status_code=200)

    _, state, _ = handler.core_pipeline.pipeline.get_state(0)
    pipeline_state = state.value_nick.upper() if state else "UNKNOWN"
    mainloop_ok = bool(handler.mainloop and handler.mainloop.is_running())
    uptime = handler.get_uptime() if hasattr(handler, 'get_uptime') else 0

    errors = []
    for ptype in ("inputs", "outputs", "encoders"):
        for p in handler._pipelines.get(ptype, []):
            if hasattr(p, 'data') and getattr(p.data, 'state', None) == "ERROR":
                errors.append({"type": ptype.rstrip('s'), "uid": str(p.data.uid), "name": getattr(p.data, 'name', '')})

    healthy = pipeline_state == "PLAYING" and mainloop_ok
    status = "ok" if healthy and not errors else "degraded" if healthy else "error"
    status_code = 200 if healthy else 503

    # anonymous callers get stripped payload (no infra detail / error list)
    is_authenticated = True
    if is_auth_enabled():
        try:
            is_authenticated = bool(await get_current_user(request))
        except Exception:
            is_authenticated = False

    if is_authenticated:
        return JSONResponse({
            "status": status,
            "pipeline": pipeline_state,
            "glib_mainloop": mainloop_ok,
            "uptime": uptime,
            "errors": errors,
        }, status_code=status_code)

    return JSONResponse({
        "status": status,
        "uptime": uptime,
        "pipeline": pipeline_state,
        "error_count": len(errors),
    }, status_code=status_code)


@router.get("/config", dependencies=[require_read()])
def get_safe_config():
    """Return config without sensitive fields (secrets, credentials)."""
    full = config.get_config()
    safe = {}
    for section, values in full.items():
        if section == 'auth':
            # Strip secrets, keep only public auth settings
            safe['auth'] = {k: v for k, v in values.items()
                           if k not in ('cookie_secret', 'client_secret', 'api_tokens')}
        elif section == 'proxy':
            # Strip credentials from proxy configs
            safe['proxy'] = {}
            for name, proxy in values.items():
                safe['proxy'][name] = {k: v for k, v in proxy.items()
                                       if k not in ('password', 'secret', 'token', 'api_key')}
        elif section == 'webrtc':
            # Strip TURN credentials
            safe['webrtc'] = {k: v for k, v in values.items()
                             if k not in ('turn_password',)}
        else:
            safe[section] = values
    return safe

@router.get("/config/preview_enabled", dependencies=[require_read()])
def get_preview_enabled():
    return config.get_preview_enabled()

@router.get("/config/mixers", dependencies=[require_read()])
def get_mixers_config():
    return config.get_scenes()

@router.get("/config/resolutions", dependencies=[require_read()])
def get_resolutions_config():
    return config.get_resolutions()

@router.get("/config/default_resolution", dependencies=[require_read()])
def get_default_resolution_config():
    return config.get_default_resolution()

@router.get("/config/proxy_types", dependencies=[require_read()])
def get_proxy_types_config():
    return config.get_proxy_types()


@router.get("/config/encoder", dependencies=[require_read()])
def get_encoder_config():
    return get_encoder_types()

@router.get("/config/elements", dependencies=[require_read()])
def get_available_elements():
    from pipelines.element_registry import get_available_audio_filters, get_available_video_filters
    return {
        'audio_filters': get_available_audio_filters(),
        'video_filters': get_available_video_filters(),
    }


def _get_viewer_count():
    from api.websockets import manager
    return len(manager.active_connections)


@router.get("/load", dependencies=[require_read()])
def get_load(request: Request):
    load1, load5, load15 = os.getloadavg()
    cpu_count = os.cpu_count() or 1

    handler = request.app.state.pipeline_handler
    inputs = len(handler._pipelines.get("inputs", [])) if handler and handler._pipelines else 0
    outputs = len(handler._pipelines.get("outputs", [])) if handler and handler._pipelines else 0
    mixers = len(handler._pipelines.get("mixers", [])) if handler and handler._pipelines else 0

    preview_fps = _get_current_preview_fps(handler)

    uptime = handler.get_uptime() if handler and hasattr(handler, 'get_uptime') else 0

    # Memory stats — includes child processes (browsers, etc.)
    mem = {}
    try:
        # Build pid→(ppid, name, rss_kb) map from /proc
        proc_info = {}
        for entry in os.listdir('/proc'):
            if not entry.isdigit():
                continue
            try:
                pid = int(entry)
                ppid = 0
                name = ''
                rss_kb = 0
                with open(f'/proc/{pid}/status') as f:
                    for line in f:
                        if line.startswith('PPid:'):
                            ppid = int(line.split()[1])
                        elif line.startswith('Name:'):
                            name = line.split(':', 1)[1].strip()
                        elif line.startswith('VmRSS:'):
                            rss_kb = int(line.split()[1])
                proc_info[pid] = (ppid, name, rss_kb)
            except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
                continue

        # Find all descendant PIDs
        my_pid = os.getpid()
        descendants = set()
        queue = [my_pid]
        while queue:
            p = queue.pop()
            descendants.add(p)
            for pid, (ppid, _, _) in proc_info.items():
                if ppid == p and pid not in descendants:
                    queue.append(pid)

        # Sum RSS across process tree
        total_rss_kb = sum(proc_info[p][2] for p in descendants if p in proc_info)
        mem['rss_mb'] = round(total_rss_kb / 1024)

        # Per-process breakdown (top consumers)
        procs = []
        for pid in descendants:
            if pid in proc_info:
                _, name, rss_kb = proc_info[pid]
                if rss_kb > 0:
                    procs.append({'pid': pid, 'name': name, 'rss_mb': round(rss_kb / 1024)})
        procs.sort(key=lambda p: p['rss_mb'], reverse=True)
        mem['processes'] = procs[:10]

        # cgroup v2 memory limit
        for path in ('/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes'):
            try:
                with open(path) as f:
                    val = f.read().strip()
                    if val != 'max' and val != '9223372036854771712':
                        mem['total_mb'] = round(int(val) / 1024 / 1024)
                    break
            except FileNotFoundError:
                continue
        if 'total_mb' not in mem:
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem['total_mb'] = round(int(line.split()[1]) / 1024)
                        break
    except Exception:
        pass

    return {
        "load1": round(load1, 2),
        "load5": round(load5, 2),
        "load15": round(load15, 2),
        "cpu_count": cpu_count,
        "load_percent": round(load1 / cpu_count * 100, 1),
        "inputs": inputs,
        "outputs": outputs,
        "mixers": mixers,
        "preview_fps": preview_fps,
        "uptime": uptime,
        "memory": mem,
        "viewers": _get_viewer_count(),
    }


class PreviewFpsDTO(BaseModel):
    fps: int


@router.put("/load/preview_fps", dependencies=[require_role("admin")])
def set_preview_fps(request: Request, data: PreviewFpsDTO):
    handler = request.app.state.pipeline_handler
    if not handler or not handler._pipelines:
        return {"error": "no pipeline handler"}

    fps = max(1, min(data.fps, 60))

    # Collect video capsfilter elements from preview output bins.
    # The capsfilter (inline caps after videorate) controls the framerate.
    # Changing its caps makes videorate drop frames to match.
    capsfilters = []
    for output in handler._pipelines.get("outputs", []):
        if not getattr(output.data, 'is_preview', False):
            continue
        obin = getattr(output, '_bin', None)
        if not obin:
            continue
        iterator = obin.iterate_recurse()
        while True:
            result, element = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            factory = element.get_factory()
            if factory and factory.get_name() == "capsfilter":
                caps = element.get_property("caps")
                if caps and caps.to_string().startswith("video/x-raw"):
                    capsfilters.append(element)
                    break

    def apply_fps():
        for cf in capsfilters:
            old_caps = cf.get_property("caps")
            s = old_caps.get_structure(0)
            new_caps = Gst.Caps.from_string(
                f"video/x-raw,format={s.get_string('format')}"
                f",width={s.get_value('width')}"
                f",height={s.get_value('height')}"
                f",framerate={fps}/1"
            )
            cf.set_property("caps", new_caps)
        return False
    GLib.idle_add(apply_fps)

    return {"fps": fps, "updated": len(capsfilters)}


@router.get("/config/export", dependencies=[require_role("supervisor")])
async def export_config(
    request: Request,
    inputs: bool = Query(True, description="Include inputs"),
    scenes: bool = Query(True, description="Include scenes and slots"),
    outputs: bool = Query(True, description="Include outputs and encoders"),
    settings: bool = Query(True, description="Include global settings"),
):
    """Export current runtime config as TOML. Filters out auto-generated preview items.

    **Security warning:** When called with settings=true as admin, the exported
    TOML contains plaintext credentials (auth.cookie_secret, auth.api_tokens).
    Treat the export file as a secret.
    """
    handler = request.app.state.pipeline_handler
    if not handler or not handler._pipelines:
        return Response(status_code=503, content="Pipeline not ready")

    export = {}

    # Global settings — admin only (may contain credentials like cookie_secret)
    if settings:
        is_admin = await _check_admin(request)
        if is_admin:
            full_config = config.get_config()
            for section in ('main', 'ui', 'preview', 'resolutions', 'webrtc', 'auth', 'proxy'):
                if section in full_config:
                    export[section] = full_config[section]

    if inputs:
        export['inputs'] = {}
        used_keys = set()
        for pipeline in handler._pipelines.get("inputs", []):
            data = pipeline.data
            input_dict = _dto_to_dict(data)
            key = _sanitize_key(data.name)
            if key in used_keys:
                key = f"{key}_{str(data.uid)[:8]}"
            used_keys.add(key)
            export['inputs'][key] = input_dict

    # Scenes + slots
    if scenes:
        export['scenes'] = {}
        for pipeline in handler._pipelines.get("mixers", []):
            data = pipeline.data
            if data.type == "scene":
                scene_key = _sanitize_key(data.name)
                scene_dict = {
                    'type': 'scene',
                    'name': data.name,
                }
                if data.locked:
                    scene_dict['locked'] = True
                if data.src_locked:
                    scene_dict['src_locked'] = True
                # Scene-level filters
                if data.audio_filters:
                    scene_dict['audio_filters'] = [f.model_dump() for f in data.audio_filters]
                if data.video_filters:
                    scene_dict['video_filters'] = [f.model_dump() for f in data.video_filters]
                for i, source in enumerate(data.sources):
                    slot_key = f"slot{i}"
                    slot_dict = {}
                    for prop in ('alpha', 'xpos', 'ypos', 'width', 'height', 'zorder', 'volume', 'mute', 'name'):
                        val = getattr(source, prop, None)
                        if val is not None:
                            slot_dict[prop] = val
                    if source.audio_filters:
                        slot_dict['audio_filters'] = [f.model_dump() for f in source.audio_filters]
                    if source.video_filters:
                        slot_dict['video_filters'] = [f.model_dump() for f in source.video_filters]
                    if source.src:
                        src_input = handler.get_pipeline("inputs", source.src)
                        if src_input:
                            slot_dict['input'] = {'type': src_input.data.type, 'name': src_input.data.name}
                    scene_dict[slot_key] = slot_dict
                export['scenes'][scene_key] = scene_dict
            elif data.type == "program":
                pass  # Program active state is runtime, not config

    if outputs:
        export['outputs'] = {}
        for pipeline in handler._pipelines.get("outputs", []):
            data = pipeline.data
            if getattr(data, 'is_preview', False):
                continue
            output_dict = _dto_to_dict(data)
            key = _sanitize_key(getattr(data, 'name', str(data.uid)))
            export['outputs'][key] = output_dict

        export['encoders'] = {}
        for pipeline in handler._pipelines.get("encoders", []):
            data = pipeline.data
            if getattr(data, 'is_preview', False):
                continue
            encoder_dict = _dto_to_dict(data)
            key = _sanitize_key(getattr(data, 'name', str(data.uid)))
            export['encoders'][key] = encoder_dict

    export = {k: v for k, v in export.items() if v}

    toml_str = toml.dumps(export)
    return Response(
        content=toml_str,
        media_type="application/toml",
        headers={"Content-Disposition": "attachment; filename=dove-config.toml"},
    )


def _dto_to_dict(dto):
    """Convert a Pydantic DTO to a clean dict, dropping None values and internal fields."""
    exclude = {'uid', 'state', 'details', 'buffering', 'position', 'duration',
               'has_video', 'has_audio', 'is_preview', 'show_controls', 'sources',
               'playlist', 'index', 'total_duration', 'total_position', 'looping',
               'current_clip', 'order'}
    result = {}
    for key, value in dto.model_dump().items():
        if key in exclude:
            continue
        if value is None:
            continue
        # Skip empty lists/dicts
        if isinstance(value, (list, dict)) and not value:
            continue
        # Convert UUID to string
        if hasattr(value, 'hex'):
            value = str(value)
        # Ensure numeric types aren't strings
        if isinstance(value, str):
            try:
                if '.' in value:
                    value = float(value)
                elif value.isdigit():
                    value = int(value)
            except (ValueError, AttributeError):
                pass
        result[key] = value
    return result


def _sanitize_key(name):
    """Convert a display name to a TOML-safe key."""
    return name.lower().replace(' ', '_').replace('-', '_')[:32] if name else 'unnamed'


async def _check_admin(request: Request) -> bool:
    """Check if the current user has admin role. Returns True if auth disabled."""
    from api.auth import is_auth_enabled, get_current_user, _get_config
    if not is_auth_enabled():
        return True
    try:
        user = await get_current_user(request)
        if not user:
            return False
        cfg = _get_config()
        groups_map = cfg.get('groups', {})
        admin_group = groups_map.get('admin', 'dove-admin')
        return admin_group in user.groups
    except Exception:
        return False


def _get_current_preview_fps(handler):
    """Get framerate from first preview output's video capsfilter."""
    if not handler or not handler._pipelines:
        return None
    for output in handler._pipelines.get("outputs", []):
        if not getattr(output.data, 'is_preview', False):
            continue
        obin = getattr(output, '_bin', None)
        if not obin:
            continue
        iterator = obin.iterate_recurse()
        while True:
            result, element = iterator.next()
            if result != Gst.IteratorResult.OK:
                break
            factory = element.get_factory()
            if factory and factory.get_name() == "capsfilter":
                caps = element.get_property("caps")
                if caps and caps.to_string().startswith("video/x-raw"):
                    s = caps.get_structure(0)
                    ok, num, den = s.get_fraction("framerate")
                    if ok and den > 0:
                        return num // den
    return None