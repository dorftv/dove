from api.inputs.cefsrc import CefsrcInputDTO
from .input import Input


class CefsrcInput(Input):
    data: CefsrcInputDTO

    def build_pipeline_str(self) -> str:
        """Return pipeline string fragment for this input."""
        uid = self.data.uid
        add_borders = "true" if getattr(self.data, 'fit', True) else "false"
        # Video pipeline: cefsrc → cefdemux → video processing → caps → tee
        video_str = (
            f' cefsrc url="{self.data.url or ""}" do-timestamp=true name=cefsrc_{uid} ! '
            f"cefdemux name=cefdemux_{uid} "
            f"cefdemux_{uid}.video ! videoconvert ! videoscale name=videoscale_{uid} add-borders={add_borders} ! videorate skip-to-first=true ! "
            f"video/x-raw,width={self.data.width},height={self.data.height},format=BGRA ! "
            f"videoconvert ! {self.get_video_end()} "
        )
        # Audio pipeline: cefdemux audio pad → audioconvert → audioresample → caps → tee
        audio_str = (
            f" cefdemux_{uid}.audio ! audioconvert ! audioresample ! "
            f"{self.get_caps('audio')} ! {self.get_audio_end()} "
        )
        return video_str + audio_str
