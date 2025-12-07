import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from api.helper import get_encoder_types
from api.auth import require_role
from gi.repository import Gst, GLib

from config_handler import ConfigReader
config = ConfigReader()

router = APIRouter(prefix="/api")


@router.get("/healthz")
def healthz(request: Request):
    handler = request.app.state._state.get("pipeline_handler")
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

    return JSONResponse({
        "status": status,
        "pipeline": pipeline_state,
        "glib_mainloop": mainloop_ok,
        "uptime": uptime,
        "errors": errors,
    }, status_code=200 if healthy else 503)


@router.get("/config", dependencies=[require_role("user")])
def get_full_config():
    return config.get_config()

@router.get("/config/preview_enabled", dependencies=[require_role("user")])
def get_preview_enabled():
    return config.get_preview_enabled()

@router.get("/config/mixers", dependencies=[require_role("user")])
def get_mixers_config():
    return config.get_mixers()

@router.get("/config/resolutions", dependencies=[require_role("user")])
def get_resolutions_config():
    return config.get_resolutions()

@router.get("/config/default_resolution", dependencies=[require_role("user")])
def get_default_resolution_config():
    return config.get_default_resolution()

@router.get("/config/proxy_types", dependencies=[require_role("user")])
def get_proxy_types_config():
    return config.get_proxy_types()


@router.get("/config/encoder", dependencies=[require_role("user")])
def get_encoder_config():
    return get_encoder_types()

@router.get("/config/elements", dependencies=[require_role("user")])
def get_available_elements():
    from pipelines.element_registry import get_available_audio_filters, get_available_video_filters
    return {
        'audio_filters': get_available_audio_filters(),
        'video_filters': get_available_video_filters(),
    }


def _get_viewer_count():
    from api.websockets import manager
    return len(manager.active_connections)


@router.get("/load", dependencies=[require_role("user")])
def get_load(request: Request):
    load1, load5, load15 = os.getloadavg()
    cpu_count = os.cpu_count() or 1

    handler = request.app.state._state.get("pipeline_handler")
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
    handler = request.app.state._state.get("pipeline_handler")
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

    # Change capsfilter framerate on GLib thread
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