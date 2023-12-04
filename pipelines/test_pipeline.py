from .base import Pipeline

class TestPipeline(Pipeline):
    pipeline_str = "v4l2src device=/dev/video0 ! videoconvert ! videoscale ! video/x-raw,width=320,height=240 ! theoraenc ! oggmux ! tcpserversink host=127.0.0.1 port=8080"