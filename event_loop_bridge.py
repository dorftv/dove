"""
Bridge between GLib MainLoop and asyncio event loop.

This module provides thread-safe mechanisms for:
1. Scheduling async coroutines from GLib callbacks
2. Running sync functions in the GLib main loop from async context
3. Managing a shared asyncio event loop reference

The GStreamer application runs two event loops:
- GLib MainLoop in the main thread (for GStreamer)
- asyncio event loop in the API thread (for FastAPI/uvicorn)

This bridge allows safe communication between them.
"""

import asyncio
import threading
from typing import Callable, Coroutine, Any, Optional

from gi.repository import GLib
from logger import logger


def _task_exception_handler(task: asyncio.Task):
    """Log exceptions from fire-and-forget async tasks."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.log(f"Async task failed: {exc}", level='ERROR')


class EventLoopBridge:
    """Singleton bridging GLib MainLoop and asyncio event loop."""

    _instance: Optional['EventLoopBridge'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
        self._asyncio_thread: Optional[threading.Thread] = None

    @classmethod
    def get_instance(cls) -> 'EventLoopBridge':
        """Get the singleton instance of EventLoopBridge."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set_asyncio_loop(self, loop: asyncio.AbstractEventLoop, thread: threading.Thread):
        """Register the asyncio event loop (called from API thread startup)."""
        self._asyncio_loop = loop
        self._asyncio_thread = thread

    def schedule_async(self, coro: Coroutine) -> None:
        """Schedule an async coroutine from a GLib callback. Thread-safe via call_soon_threadsafe."""
        if self._asyncio_loop is None:
            # Event loop not yet registered, silently skip
            return

        if threading.current_thread() == self._asyncio_thread:
            # Already in asyncio thread, create task directly
            task = asyncio.create_task(coro)
            task.add_done_callback(_task_exception_handler)
        else:
            # Cross-thread: use threadsafe scheduling
            def _create():
                task = asyncio.create_task(coro)
                task.add_done_callback(_task_exception_handler)
            self._asyncio_loop.call_soon_threadsafe(_create)

    def run_sync_in_glib(self, func: Callable, *args) -> None:
        """Schedule a synchronous function to run in GLib main loop (from asyncio context)."""
        GLib.idle_add(func, *args)

    def call_glib_async(self, func: Callable, *args) -> asyncio.Future:
        """Run func on GLib main loop, return awaitable Future with its result."""
        if self._asyncio_loop is None:
            raise RuntimeError("asyncio loop not registered on bridge")

        loop = self._asyncio_loop
        future: asyncio.Future = loop.create_future()

        def _runner():
            try:
                result = func(*args)
                loop.call_soon_threadsafe(future.set_result, result)
            except Exception as e:
                loop.call_soon_threadsafe(future.set_exception, e)
            return False

        GLib.idle_add(_runner)
        return future


# Module-level singleton access
bridge = EventLoopBridge.get_instance()


def safe_broadcast(channel: str, data: Any, type: str = "") -> None:
    """Broadcast to WebSocket clients from any context (GLib or asyncio); auto-detects scheduling."""
    from api.websockets import manager

    coro = manager.broadcast(channel, data, type)

    try:
        # Check if we're in an async context
        asyncio.get_running_loop()
        # We are in async context - create task directly
        task = asyncio.create_task(coro)
        task.add_done_callback(_task_exception_handler)
    except RuntimeError:
        # Not in async context (GLib callback) - schedule via bridge
        bridge.schedule_async(coro)
