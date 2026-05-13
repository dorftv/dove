from dove.api.inputs.v4l2src import V4l2srcInputDTO
from .input import Input


class V4l2srcInput(Input):
    data: V4l2srcInputDTO

    def build_pipeline_str(self) -> str:
        """Return pipeline string fragment for this input."""
        uid = self.data.uid
        add_borders = "true" if getattr(self.data, 'fit', True) else "false"
        video_str = (
            f" v4l2src device={self.data.device} do-timestamp=true "
            f" name=v4l2src_{uid} ! video/x-raw ! videoconvert ! videoscale name=videoscale_{uid} add-borders={add_borders} ! "
            f" {self.get_caps('video')} ! {self.get_video_end()} "
        )
        if self.data.audio_device:
            audio_str = (
                f' alsasrc device="{self.data.audio_device}" do-timestamp=true '
                f" name=alsasrc_{uid} ! audioconvert ! audioresample ! "
                f" {self.get_caps('audio')} ! {self.get_audio_end()} "
            )
        else:
            self.data.has_audio = False
            audio_str = ""
        return video_str + audio_str
