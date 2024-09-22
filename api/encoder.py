from typing import Annotated, Optional, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class EncoderDTO(BaseModel):
    name: str
    options: Optional[str] = ""

class muxDTO(BaseModel):
    name: str
    options: Optional[str] = ""

class mpegtsMuxDTO(muxDTO):
    name: Literal["mpegts"] = "mpegts"
    element: Literal["mpegtsmux"] = "mpegtsmux"
    options: Optional[str] = ""

class flvMuxDTO(muxDTO):
    name: Literal["flvmux"] = "flvmux"
    element: Literal["flvmux"] = "flvmux"
    options: Optional[str] = ""

class videoEncoderDTO(EncoderDTO):
    type: Literal["video"] = "video"
    profile: Optional[str] = None
    level: Optional[str] = None

class audioEncoderDTO(EncoderDTO):
    type: Literal["audio"] = "audio"

#    h264_profile: Optional[str] = Field(
#        default="baseline",
#        label="X264 Profile",
#        description="h264 profile to use (high-4:4:4, high-4:2:2, high-10, high, main, baseline, constrained-baseline, high-4:4:4-intra, high-4:2:2-intra, high-10-intra))",
#        placeholder="baseline"

class x264EncoderDTO(videoEncoderDTO):
    name: Literal["x264"] = "x264"
    element: Literal["x264enc"] = "x264enc"
    profile: Optional[str] = "main"

class vah264encEncoderDTO(videoEncoderDTO):
    name: Literal["vah264enc"] = "vah264enc"
    element: Literal["vah264enc"] = "vah264enc"
    profile: Optional[str] = "main"

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

