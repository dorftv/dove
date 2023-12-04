from abc import ABC, abstractmethod

import gi 
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

    def __init__(self):
        assert self.get_pipeline_str() is not None, "pipeline_str must be set"
        self.parsed = Gst.parse_launch(self.get_pipeline_str())


    @abstractmethod
    def get_pipeline_str(self):
        return self.pipeline_str
    
    def play(self):
        self.parsed.set_state(Gst.State.PLAYING)
    
    def pause(self):
        self.parsed.set_state(Gst.State.PAUSED)
