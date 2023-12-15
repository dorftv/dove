from input import Input

class TestInput(Input):
    def build(self):
        video_pipeline_str = "videotestsrc pattern=1 is_live=true !" + self.get_video_end()
        audio_pipeline_str = "audiotestsrc wave=2 freq=600 is-live=true volume=0.5 ! audioresample ! audioconvert !" + self.get_audio_end()
        self.add_pipeline(video_pipeline_str)
        self.add_pipeline(audio_pipeline_str)
