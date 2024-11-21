from typing import Annotated, Optional, Literal, Union
from pydantic import BaseModel, Field
from .encoder import EncoderDTO


class videoEncoderDTO(EncoderDTO):
    type: Literal["video"] = "video"


class h264EncoderDTO(videoEncoderDTO):
    profile: Optional[str] =  Field(
        label = "Profile",
        description = "H264 Profile. eg. Main, High, Baseline",
        default = "high",
        placeholder =  "high",
    )

class x264EncoderDTO(h264EncoderDTO):
    name: Literal["x264"] = "x264"
    element: Literal["x264enc"] = "x264enc"
    options: Optional[str] = Field(
        label = "x264enc options",
        description = "Options for x264enc.",
        default = "key-int-max=25 speed-preset=veryfast",
        placeholder = "key-int-max=30 speed-preset=veryfast",
    )

class x265EncoderDTO(videoEncoderDTO):
    name: Literal["x265"] = "x265"
    element: Literal["x265enc"] = "x265enc"

class openh264EncoderDTO(h264EncoderDTO):
    name: Literal["openh264enc"] = "openh264enc"
    element: Literal["openh264enc"] = "openh264enc"

class vah264encEncoderDTO(h264EncoderDTO):
    name: Literal["vah264enc"] = "vah264enc"
    element: Literal["vah264enc"] = "vah264enc"
    options: Optional[str] = Field(
        label = "vah264enc options",
        description = "Options for vah264enc.",
        default = "",
        placeholder = "",
    )

class vah264lpencEncoderDTO(h264EncoderDTO):
    name: Literal["vah264lpenc"] = "vah26lpenc"
    element: Literal["vah264lpenc"] = "vah264lpenc"

class vaapih264encEncoderDTO(h264EncoderDTO):
    name: Literal["vaapih264enc"] = "vaapih264enc"
    element: Literal["vaapih264enc"] = "vaapih264enc"


class mpph264encEncoderDTO(h264EncoderDTO):
    name: Literal["mpph264enc"] = "mpph264enc"
    element: Literal["mpph264enc"] = "mpph264enc"


############################################################################

h264EncoderUnion = Annotated[
    Union[x264EncoderDTO, openh264EncoderDTO, vaapih264encEncoderDTO, vah264encEncoderDTO, vah264lpencEncoderDTO, mpph264encEncoderDTO],
    Field(discriminator='name')
]

h265EncoderUnion = Annotated[
    Union[x265EncoderDTO],
    Field(discriminator='name')
]
