import os, gi
gi.require_version("Gst", "1.0")
from gi.repository import GObject, Gst, GLib

class Pipeline:
    def __init__(self, url, local_file, width, height):
        self.url = url
        self.local_file = local_file
        self.width = width
        self.height = height

        Gst.init(None)

    def _build_overlay_pipe(self):
        compositor = f"compositor name=overlay src::alpha=1 htmloverlay::alpha=1 !  video/x-raw,width={self.width},height={self.height} ! videorate ! videoconvert ! queue ! autovideosink"
        uridecodebin = f"uridecodebin3 uri=file:///home/hatsch/Videos/banane.mp4 !  video/x-raw,width={self.width},height={self.height} ! videorate !  videoconvert ! queue ! overlay."
        wpesrc = f"wpesrc location={ self.url }  draw-background=false  name=htmloverlay !  video/x-raw,width={self.width},height={self.height} ! videorate ! videoconvert ! queue ! overlay."

        return Gst.parse_launch(" ".join([compositor, uridecodebin, wpesrc]))

    def build(self):
        src1 = Gst.parse_launch(f"uridecodebin3 uri=file://{self.local_file} !   video/x-raw ! videoconvert ! interpipesink name=src1_sink async=true sync=true")
        fake = Gst.parse_launch(f"interpipesrc listen-to=src1_sink name=src format=time allow-renegotiation=true   !  video/x-raw,width={self.width},height={self.height} ! videoconvert ! queue ! autovideosink ")
        html_src = Gst.parse_launch(f" wpesrc location=https://dorftv.at draw-background=false !  video/x-raw,width={self.width},height={self.height},mode=ARGB ! videoconvert ! queue ! interpipesink name=html_src_sink")
        self.overlaypipe = self._build_overlay_pipe()

        finalpipe = Gst.parse_launch(f"interpipesrc listen-to=finalsink allow-renegotiation=true format=time ! video/x-raw,width={self.width},height={self.height} !  videoconvert ! queue ! autovideosink")

        src1.set_state(Gst.State.PLAYING)
        html_src.set_state(Gst.State.PLAYING)

        self.overlaypipe.set_state(Gst.State.PLAYING)
        finalpipe.set_state(Gst.State.PLAYING)

    def switch(self):
        # TODO ?
        src = self.overlaypipe.get_by_name('src')
        src.set_property("listen-to", "")

    def run(self):
        gst_loop = GLib.MainLoop()
        gst_loop.run()

