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
    """
    Singleton that bridges GLib MainLoop and asyncio event loop.

    Usage:
        bridge = EventLoopBridge.get_instance()

        # From GLib callback, schedule async work:
        bridge.schedule_async(manager.broadcast("UPDATE", data))

        # From async context, run in GLib loop:
        bridge.run_sync_in_glib(some_glib_function, arg1, arg2)
    """

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
        """
        Register the asyncio event loop (called from API thread startup).

        Args:
            loop: The asyncio event loop running in the API thread
            thread: The thread running the asyncio event loop
        """
        self._asyncio_loop = loop
        self._asyncio_thread = thread

    def schedule_async(self, coro: Coroutine) -> None:
        """
        Schedule an async coroutine from a GLib callback (non-async context).

        Thread-safe: Uses call_soon_threadsafe to schedule on asyncio loop.

        Args:
            coro: The coroutine to schedule
        """
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
        """
        Schedule a synchronous function to run in GLib main loop.

        Use from asyncio context when you need to interact with GStreamer.

        Args:
            func: The function to run in GLib context
            *args: Arguments to pass to the function
        """
        GLib.idle_add(func, *args)


# Module-level singleton access
bridge = EventLoopBridge.get_instance()


def safe_broadcast(channel: str, data: Any, type: str = "") -> None:
    """
    Broadcast to WebSocket clients from any context (GLib or asyncio).

    Automatically detects context and uses appropriate scheduling.

    Args:
        channel: The broadcast channel (e.g., "UPDATE", "CREATE", "DELETE")
        data: The data to broadcast (must have .dict() method)
        type: Optional type override (e.g., "input", "output", "mixer")
    """
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
