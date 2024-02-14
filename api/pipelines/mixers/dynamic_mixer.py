from pathlib import Path
from typing import Optional

from pipelines.mixers.mixer import Mixer
from api.mixers_dtos import dynamicMixerDTO


class dynamicMixer(Mixer):
    data: dynamicMixerDTO
    

    def build(self):
        # @TODO improve caps handling
        caps = f"video/x-raw,width={self.data.width},height={self.data.height},format=BGRA"
        audio_caps = "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2"
        print(self.data.uid)
        self.add_pipeline("videotestsrc pattern=0 is-live=true ! "
            f" { caps }!  queue !"
            f" compositor name=videomixer_{self.data.uid} sink_0::alpha=1 sink_1::alpha=1 ! { caps } ! "
            + self.get_video_end() + 
            f" audiotestsrc volume=0 ! { audio_caps } ! audiomixer name=audiomixer_{self.data.uid} ! "
            + self.get_audio_end())

    def switch_src(self, src: str):
        elm = self.inner_pipelines[0].get_by_name(f"output_{self.uid}")
        elm.set_property("listen_to", src)

    def describe(self):
        return self.data
