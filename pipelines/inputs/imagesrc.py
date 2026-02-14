from api.inputs.imagesrc import ImagesrcInputDTO
from .input import Input
from gi.repository import Gst
from logger import logger
from event_loop_bridge import safe_broadcast


class ImagesrcInput(Input):
    data: ImagesrcInputDTO

    def build_pipeline_str(self) -> str:
        raise NotImplementedError("ImagesrcInput uses build_bin()")

    def build_bin(self) -> Gst.Bin:
        uid = self.data.uid
        location = self.data.location
        self.data.has_audio = False

        container = Gst.Bin.new(f"input_bin_{uid}")

        # --- Video chain: filesrc → decodebin3 → imagefreeze → convert → tee ---
        filesrc = Gst.ElementFactory.make("filesrc", f"filesrc_{uid}")
        filesrc.set_property("location", location)

        decodebin = Gst.ElementFactory.make("decodebin3", f"decodebin_{uid}")

        imagefreeze = Gst.ElementFactory.make("imagefreeze", f"imagefreeze_{uid}")
        imagefreeze.set_property("is-live", True)

        videoconvert = Gst.ElementFactory.make("videoconvert", f"videoconvert_{uid}")
        videoscale = Gst.ElementFactory.make("videoscale", f"videoscale_{uid}")
        videoscale.set_property("add-borders", self.data.fit if self.data.fit is not None else True)
        videorate = Gst.ElementFactory.make("videorate", f"videorate_{uid}")
        videorate.set_property("skip-to-first", True)
        vcapsfilter = Gst.ElementFactory.make("capsfilter", f"vcapsfilter_{uid}")
        vcapsfilter.set_property("caps", Gst.Caps.from_string(self.get_caps('video')))

        video_tee = Gst.ElementFactory.make("tee", f"video_tee_{uid}")
        video_tee.set_property("allow-not-linked", True)

        video_fakesink = Gst.ElementFactory.make("fakesink", f"video_fakesink_{uid}")
        video_fakesink.set_property("sync", False)
        video_fakesink.set_property("async", False)
        vqueue_sync = Gst.ElementFactory.make("queue", f"vqueue_sync_{uid}")
        vqueue_sync.set_property("leaky", 2)
        vqueue_sync.set_property("max-size-buffers", 1)

        # --- Add all elements ---
        for elem in [filesrc, decodebin, imagefreeze,
                     videoconvert, videoscale, videorate, vcapsfilter,
                     video_tee, vqueue_sync, video_fakesink]:
            container.add(elem)

        # --- Link static chains ---
        filesrc.link(decodebin)
        # decodebin → imagefreeze linked dynamically via pad-added
        imagefreeze.link(videoconvert)
        videoconvert.link(videoscale)
        videoscale.link(videorate)
        videorate.link(vcapsfilter)
        vcapsfilter.link(video_tee)
        video_tee.link(vqueue_sync)
        vqueue_sync.link(video_fakesink)

        # --- Dynamic pad linking ---
        video_linked = [False]

        def on_pad_added(element, pad):
            try:
                caps = pad.get_current_caps() or pad.query_caps(None)
                if not caps or caps.get_size() == 0:
                    return
                name = caps.get_structure(0).get_name()
                if name.startswith("video/") and not video_linked[0]:
                    sink_pad = imagefreeze.get_static_pad("sink")
                    if not sink_pad.is_linked():
                        pad.link(sink_pad)
                        video_linked[0] = True
                        self.data.has_video = True
                        self.data.state = "PLAYING"
                        safe_broadcast("UPDATE", self.data)
                        logger.log(f"imagesrc {uid}: video pad linked", level='DEBUG')
                elif name.startswith("audio/"):
                    logger.log(f"imagesrc {uid}: ignoring audio pad from image", level='DEBUG')
                else:
                    logger.log(f"imagesrc {uid}: rejecting non-image pad: {name}", level='WARNING')
            except Exception as e:
                logger.log(f"imagesrc {uid} pad-added error: {e}", level='ERROR')

        decodebin.connect("pad-added", on_pad_added)

        # --- Store references ---
        self.video_tee = video_tee
        self.audio_tee = None
        self.volume_element = None

        logger.log(f"imagesrc bin created for {uid}: location={location}", level='DEBUG')
        return container

    def handle_error(self, err_message):
        logger.log(f"imagesrc {self.data.uid} error: {err_message}", level='ERROR')
        self.data.state = "ERROR"
        self.data.details = err_message
        safe_broadcast("UPDATE", self.data)
