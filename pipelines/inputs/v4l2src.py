from api.inputs.v4l2src import V4l2srcInputDTO
from .input import Input


class V4l2srcInput(Input):
    data: V4l2srcInputDTO

    def build_pipeline_str(self) -> str:
        """Return pipeline string fragment for this input."""
        uid = self.data.uid
        if self.data.audio_device:
            audio_src = (
                f' alsasrc device="{self.data.audio_device}" do-timestamp=true '
                f" name=alsasrc_{uid} ! audioconvert ! audioresample ! "
            )
        else:
            audio_src = (
                f" audiotestsrc wave=4 volume=0 do-timestamp=true is-live=true "
                f" name=audiotestsrc_{uid} ! "
            )
        add_borders = "true" if getattr(self.data, 'fit', True) else "false"
        return (
            f" v4l2src device={self.data.device} do-timestamp=true "
            f" name=v4l2src_{uid} ! video/x-raw ! videoconvert ! videoscale name=videoscale_{uid} add-borders={add_borders} ! "
            f" {self.get_caps('video')} ! {self.get_video_end()} "
            f" {audio_src} {self.get_caps('audio')} ! {self.get_audio_end()} "
        )
