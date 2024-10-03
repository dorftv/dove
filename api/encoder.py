from typing import Annotated, Optional, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class EncoderDTO(BaseModel):
    name: str
    options: Optional[str] = Field(
        label = "Options",
        description = "Options",
        default = "",
        placeholder =  "",
    )

#########################
##MUX####################

class muxDTO(EncoderDTO):
    name: str

class mpegtsMuxDTO(muxDTO):
    name: Literal["mpegtsmux"] = "mpegtsmux"
    element: Literal["mpegtsmux"] = "mpegtsmux"
    options: Optional[str] = Field(
        label = "Mpegtsmux options",
        description = "Options for mpegtsmux.",
        default = "",
        placeholder =  "",
    )
class flvMuxDTO(muxDTO):
    name: Literal["flvmux"] = "flvmux"
    element: Literal["flvmux"] = "flvmux"
    options: Optional[str] = Field(
        label = "Flvmux options",
        description = "Options for flvmux.",
        default = "",
        placeholder =  "",
    )

#######################
##VIDEO################

class videoEncoderDTO(EncoderDTO):
    type: Literal["video"] = "video"

class x264EncoderDTO(videoEncoderDTO):
    name: Literal["x264"] = "x264"
    element: Literal["x264enc"] = "x264enc"
    options: Optional[str] = Field(
        label = "x264enc options",
        description = "Options for x264enc.",
        default = "key-int-max=30 speed-preset=veryfast",
        placeholder = "key-int-max=30 speed-preset=veryfast",
    )

    profile: Optional[str] =  Field(
        label = "Profile",
        description = "H264 Profile. eg. Main, High, Baseline",
        default = "main",
        placeholder =  "main",
    )

class openh264EncoderDTO(videoEncoderDTO):
    name: Literal["openh264enc"] = "openh264enc"
    element: Literal["openh264enc"] = "openh264enc"

class vah264encEncoderDTO(videoEncoderDTO):
    name: Literal["vah264enc"] = "vah264enc"
    element: Literal["vah264enc"] = "vah264enc"
    options: Optional[str] = Field(
        label = "vah264enc options",
        description = "Options for vah264enc.",
        default = "",
        placeholder = "",
    )
    profile: Optional[str] =  Field(
        label = "Profile",
        description = "H264 Profile. eg. Main, High, Baseline",
        default = "high",
        placeholder =  "high",
    )
class mpph264encEncoderDTO(videoEncoderDTO):
    name: Literal["mpph264enc"] = "mpph264enc"
    element: Literal["mpph264enc"] = "mpph264enc"


#######################
##AUDIO################

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

