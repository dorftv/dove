from typing import Annotated, Optional, Literal, Union
from pydantic import Field
from .encoder import EncoderDTO

class audioEncoderDTO(EncoderDTO):
    type: Literal["audio"] = "audio"

class aacEncoderDTO(audioEncoderDTO):
    name: Literal["aac"] = "aac"
    element: Literal["voaacenc"] = "voaacenc"

class mp2EncoderDTO(audioEncoderDTO):
    name: Literal["mp2"] = "mp2"
    element: Literal["avenc_mp2"] = "avenc_mp2"
    level: Optional[int] = 1

class mp3EncoderDTO(audioEncoderDTO):
    name: Literal["mp3"] = "mp3"
    element: Literal["lamemp3enc"] = "lamemp3enc"

class opusEncoderDTO(audioEncoderDTO):
    name: Literal["opus"] = "opus"
    element: Literal["opusenc"] = "opusenc"
    options: Optional[str] = Field(
        label = "Opus Encoder options",
        description = "Options for opusenc.",
        default = "perfect-timestamp=true frame-size=5",
        placeholder = "perfect-timestamp=true frame-size=5",
    )

