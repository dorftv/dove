from pathlib import Path
from typing import Optional

from pipelines.mixers.mixer import Mixer
from api.mixers_dtos import mixerMixerDTO


class mixerMixer(Mixer):
    data: mixerMixerDTO
    output_base: Optional[Path] = "/var/dove/hls"

    def build(self):

        caps = "video/x-raw,width=1280,height=720,framerate=25/1"
        audio_caps = "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2"
        
        self.add_pipeline("videotestsrc pattern=0 is-live=true ! "
            f" { caps }!  queue !"
            f" compositor name=videomixer sink_0::alpha=1 sink_1::alpha=1 ! { caps } ! videoconvert ! videoscale ! videorate ! queue  ! "
            + self.get_video_end() + 
            f" audiotestsrc volume=0 ! { audio_caps } ! audiomixer name=audiomixer ! audioconvert ! audioresample ! { audio_caps } !  queue !"
            + self.get_audio_end())

    def switch_src(self, src: str):
        elm = self.inner_pipelines[0].get_by_name(f"output_{self.uid}")
        elm.set_property("listen_to", src)

    def describe(self):
        return self.data
