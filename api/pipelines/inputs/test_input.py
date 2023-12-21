from api.dtos import InputDTO
from .input import Input
from gi.repository import Gst
from pipelines.description import Description


class TestInput(Input):
    attrs: InputDTO

    def build(self):
        video_pipeline_str = f"videotestsrc pattern=1 is_live=true name=videotestsrc_{self.uid} !" + self.get_video_end()
        audio_pipeline_str = f"audiotestsrc wave=2 freq=600 is-live=true volume=0.5 name=audiotestsrc_{self.uid} ! audioresample ! audioconvert !" + self.get_audio_end()
        self.add_pipeline(video_pipeline_str)
        self.add_pipeline(audio_pipeline_str)

    def describe(self):
        # attrs = {
        #     "is_live_video": self.inner_pipelines[0].get_by_name(f"videotestsrc_{self.uid}").get_property("is_live"),
        #     "is_live_audio": self.inner_pipelines[1].get_by_name(f"audiotestsrc_{self.uid}").get_property("is_live"),
        #     "freq": self.inner_pipelines[1].get_by_name(f"audiotestsrc_{self.uid}").get_property("freq"),
        #     "volume": self.inner_pipelines[1].get_by_name(f"audiotestsrc_{self.uid}").get_property("volume"),
        #     "state_video": Gst.Element.state_get_name(self.inner_pipelines[0].get_state(1)[1])
        # }
        # return Description(uid=self.uid, attrs=attrs)
        return self.attrs
