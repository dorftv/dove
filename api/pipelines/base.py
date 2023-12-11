import uuid
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

import gi

from models import input

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# class Pipeline:
#     def __init__(self):
#         Gst.init(None)
#         self.pipeline = Gst.parse_launch("v4l2src device=/dev/video0 ! videoconvert ! videoscale ! video/x-raw,width=320,height=240 ! theoraenc ! oggmux ! tcpserversink host=127.0.0.1 port=8080")

#     def start(self):
#         self.pipeline.set_state(Gst.State.PLAYING)
#         self.loop = GLib.MainLoop()
#         self.loop.run()
    
#     def stop(self):
#         self.loop.quit()

class Pipeline(ABC):
    pipeline_str: str

    uid: UUID
    name: str
    height: int
    width: int
    preview: bool
    state: str

    def __init__(self, uid: Optional[UUID] = None, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        if not uid:
            self.uid = uuid.uuid4()
        else:
            self.uid = uid

        assert self.get_pipeline_str() is not None, "pipeline_str must be set"
        self.parsed = Gst.parse_launch(self.get_pipeline_str())


    def get_pipeline_str(self):
        return self.pipeline_str

    @abstractmethod
    def describe(self) -> "input.InputCreateDTO":
        pass
    
    def play(self):
        self.parsed.set_state(Gst.State.PLAYING)
    
    def pause(self):
        self.parsed.set_state(Gst.State.PAUSED)

    def stop(self):
        self.parsed.set_state(Gst.State.NULL)

    def set_state(self, state: str):
        state = getattr(Gst.State, state)
        self.parsed.set_state(state)
