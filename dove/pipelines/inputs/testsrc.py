from dove.api.inputs.testsrc import TestsrcInputDTO
from .input import Input


class TestsrcInput(Input):
    data: TestsrcInputDTO

    def build_pipeline_str(self) -> str:
        """Return pipeline string fragment for this input."""
        uid = self.data.uid
        return (
            f" videotestsrc do-timestamp=true is-live=true pattern={self.data.pattern} "
            f" name=videotestsrc_{uid} ! {self.get_caps('video')} ! {self.get_video_end()} "
            f" audiotestsrc do-timestamp=true is-live=true wave={self.data.wave} freq={self.data.freq} "
            f" name=audiotestsrc_{uid} ! {self.get_caps('audio')} ! {self.get_audio_end()} "
        )


