import faulthandler
import os
import signal
import sys
import time
import threading
import traceback

# Crash dumps: write to /crashes if mounted, otherwise stderr
_crash_file = None
_crash_dir = os.environ.get('DOVE_CRASH_DIR', '/crashes')
if os.path.isdir(_crash_dir):
    try:
        _crash_file = open(os.path.join(_crash_dir, 'faulthandler.log'), 'a')
    except OSError:
        pass
_fault_out = _crash_file or sys.stderr
faulthandler.enable(file=_fault_out, all_threads=True)
faulthandler.register(signal.SIGUSR2, file=_fault_out, all_threads=True)

# In-process scan so we can filter harmless GstIntRange CRITICALs from Python.
os.environ.setdefault('GST_REGISTRY_FORK', 'no')

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib

def _filter_intrange_critical(domain, level, message, _user_data):
    if 'gst_value_collect_int_range' in message or 'range start is not smaller' in message:
        return
    print(f'({domain}-CRITICAL): {message}', file=sys.stderr, flush=True)

GLib.log_set_handler(
    'GStreamer', GLib.LogLevelFlags.LEVEL_CRITICAL,
    _filter_intrange_critical, None,
)

from gi.repository import Gst  # noqa: E402
Gst.init([])

from dove.api_thread import APIThread
from dove.pipeline_handler import HandlerSingleton
from dove.elements_factory import ElementsFactory


def start_glib_watchdog(interval=5, timeout=10):
    """Detect GLib main loop freezes and dump all thread stacks."""
    def watchdog():
        while True:
            time.sleep(interval)
            probe = threading.Event()
            GLib.idle_add(lambda: probe.set() or False)
            if not probe.wait(timeout=timeout):
                print("=== GLIB WATCHDOG: MAIN LOOP UNRESPONSIVE ===", file=sys.stderr, flush=True)
                for tid, frame in sys._current_frames().items():
                    name = "?"
                    for t in threading.enumerate():
                        if t.ident == tid:
                            name = t.name
                            break
                    print(f"\n--- Thread {tid} ({name}) ---", file=sys.stderr, flush=True)
                    traceback.print_stack(frame, file=sys.stderr)
                print("=== END WATCHDOG DUMP ===", file=sys.stderr, flush=True)
    threading.Thread(target=watchdog, daemon=True, name="glib-watchdog").start()


def main():
    handler = HandlerSingleton()

    from dove.pipelines.element_registry import probe_elements
    probe_elements()

    elements = ElementsFactory(handler)

    # Build minimal pipeline before mainloop (no live elements yet)
    handler.finish_initial_setup()

    # Wire name generators to check existing entities (avoids duplicate names)
    from dove.api.input_models import uniqueId as inputId
    from dove.api.mixers_dtos import uniqueId as sceneId
    from dove.api.output_models import uniqueId as outputId
    from dove.api.encoder_models import uniqueId as encoderId
    inputId.get_existing = lambda: {p.data.name for p in handler.get_pipelines('inputs') or []}
    sceneId.get_existing = lambda: {p.data.name for p in handler.get_pipelines('mixers') or []}
    outputId.get_existing = lambda: {p.data.name for p in handler.get_pipelines('outputs') or []}
    encoderId.get_existing = lambda: {p.data.name for p in handler.get_pipelines('encoders') or []}

    api = APIThread(pipeline_handler=handler)
    api.start()

    # Create entities once GLib mainloop is running (live elements need clock)
    def _on_mainloop_ready():
        elements.create_pipelines()
        return False

    handler.mainloop = GLib.MainLoop()
    GLib.idle_add(_on_mainloop_ready)
    start_glib_watchdog()

    # Graceful shutdown on SIGTERM (docker stop) and SIGINT (Ctrl+C)
    def _on_shutdown(*args):
        print("Shutting down…", file=sys.stderr, flush=True)
        handler.mainloop.quit()
        return GLib.SOURCE_REMOVE

    GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, _on_shutdown)
    GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, _on_shutdown)

    handler.mainloop.run()


if __name__ == "__main__":
    main()
