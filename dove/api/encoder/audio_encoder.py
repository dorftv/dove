from typing import ClassVar, Optional, Literal
from pydantic import Field
from .encoder import EncoderDTO
from dove.api.input_models import AudioFilterDTO

class audioEncoderDTO(EncoderDTO):
    type: Literal["audio"] = "audio"
    audio_filters: Optional[list[AudioFilterDTO]] = []

class aacEncoderDTO(audioEncoderDTO):
    name: Literal["aac"] = "aac"
    element: Literal["fdkaacenc"] = "fdkaacenc"
    format: ClassVar[str] = "S16LE"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "aacparse"

class voaacEncoderDTO(audioEncoderDTO):
    name: Literal["voaac"] = "voaac"
    element: Literal["voaacenc"] = "voaacenc"
    format: ClassVar[str] = "S16LE"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "aacparse"

class mp2EncoderDTO(audioEncoderDTO):
    name: Literal["mp2"] = "mp2"
    element: Literal["avenc_mp2"] = "avenc_mp2"
    level: Optional[int] = 1
    format: ClassVar[str] = "S16LE"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "audio/mpeg,mpegversion=1,layer=2,channels=2,mode=joint-stereo ! queue"

class mp3EncoderDTO(audioEncoderDTO):
    name: Literal["mp3"] = "mp3"
    element: Literal["lamemp3enc"] = "lamemp3enc"
    format: ClassVar[str] = "S16LE"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "queue"

class vorbisEncoderDTO(audioEncoderDTO):
    name: Literal["vorbisenc"] = "vorbisenc"
    element: Literal["vorbisenc"] = "vorbisenc"
    format: ClassVar[str] = "S16LE"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = ""

class flacEncoderDTO(audioEncoderDTO):
    name: Literal["flacenc"] = "flacenc"
    element: Literal["flacenc"] = "flacenc"
    format: ClassVar[str] = "S16LE"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = ""

class opusEncoderDTO(audioEncoderDTO):
    name: Literal["opus"] = "opus"
    element: Literal["opusenc"] = "opusenc"
    format: ClassVar[str] = ""
    pre_elements: ClassVar[str] = "audioresample ! audio/x-raw,format=S16LE,layout=interleaved,channels=1,rate=24000 ! queue"
    post_elements: ClassVar[str] = "queue"
    options: Optional[str] = Field(
        label = "Opus Encoder options",
        description = "Options for opusenc.",
        default = "perfect-timestamp=true frame-size=5",
        placeholder = "perfect-timestamp=true frame-size=5",
    )
