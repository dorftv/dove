from typing import Annotated, ClassVar, Optional, Literal, Union
from pydantic import Field
from .encoder import EncoderDTO


class videoEncoderDTO(EncoderDTO):
    type: Literal["video"] = "video"


class h264EncoderDTO(videoEncoderDTO):
    codec: ClassVar[str] = "h264"
    profile: Optional[str] =  Field(
        label = "Profile",
        description = "H264 Profile. eg. Main, High, Baseline",
        default = "main",
        placeholder =  "main",
    )

class x264EncoderDTO(h264EncoderDTO):
    name: Literal["x264"] = "x264"
    element: Literal["x264enc"] = "x264enc"
    format: ClassVar[str] = "I420"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = ""
    options: Optional[str] = Field(
        label = "x264enc options",
        description = "Options for x264enc.",
        default = "key-int-max=25 speed-preset=veryfast tune=zerolatency",
        placeholder = "key-int-max=25 speed-preset=veryfast tune=zerolatency",
    )

class openh264EncoderDTO(h264EncoderDTO):
    name: Literal["openh264enc"] = "openh264enc"
    element: Literal["openh264enc"] = "openh264enc"
    format: ClassVar[str] = "I420"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "h264parse"
    options: Optional[str] = Field(
        label = "openh264enc options",
        description = "Options for openh264enc.",
        default = "gop-size=25",
        placeholder = "gop-size=25",
    )

class vah264encEncoderDTO(h264EncoderDTO):
    name: Literal["vah264enc"] = "vah264enc"
    element: Literal["vah264enc"] = "vah264enc"
    format: ClassVar[str] = "NV12"
    pre_elements: ClassVar[str] = "vapostproc"
    post_elements: ClassVar[str] = "h264parse"
    options: Optional[str] = Field(
        label = "vah264enc options",
        description = "Options for vah264enc.",
        default = "key-int-max=25",
        placeholder = "key-int-max=25",
    )

class vah264lpencEncoderDTO(h264EncoderDTO):
    name: Literal["vah264lpenc"] = "vah264lpenc"
    element: Literal["vah264lpenc"] = "vah264lpenc"
    format: ClassVar[str] = "NV12"
    pre_elements: ClassVar[str] = "vapostproc"
    post_elements: ClassVar[str] = "h264parse"
    options: Optional[str] = Field(
        label = "vah264lpenc options",
        description = "Options for vah264lpenc.",
        default = "key-int-max=25",
        placeholder = "key-int-max=25",
    )

class vaapih264encEncoderDTO(h264EncoderDTO):
    name: Literal["vaapih264enc"] = "vaapih264enc"
    element: Literal["vaapih264enc"] = "vaapih264enc"
    format: ClassVar[str] = "NV12"
    pre_elements: ClassVar[str] = "vapostproc"
    post_elements: ClassVar[str] = "h264parse"
    options: Optional[str] = Field(
        label = "vaapih264enc options",
        description = "Options for vaapih264enc.",
        default = "keyframe-period=25",
        placeholder = "keyframe-period=25",
    )

class mpph264encEncoderDTO(h264EncoderDTO):
    name: Literal["mpph264enc"] = "mpph264enc"
    element: Literal["mpph264enc"] = "mpph264enc"
    format: ClassVar[str] = "I420"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "h264parse ! queue"

class vulkanh264encEncoderDTO(h264EncoderDTO):
    name: Literal["vulkanh264enc"] = "vulkanh264enc"
    element: Literal["vulkanh264enc"] = "vulkanh264enc"
    format: ClassVar[str] = "NV12"
    pre_elements: ClassVar[str] = "vulkanupload"
    post_elements: ClassVar[str] = "h264parse"
    options: Optional[str] = Field(
        label = "vulkanh264enc options",
        description = "Options for vulkanh264enc.",
        default = "idr-period=60",
        placeholder = "idr-period=60",
    )


class h265EncoderDTO(videoEncoderDTO):
    codec: ClassVar[str] = "h265"
    profile: Optional[str] = Field(
        label = "Profile",
        description = "H265 Profile. eg. Main, Main10",
        default = None,
        placeholder = "main",
    )

class x265EncoderDTO(h265EncoderDTO):
    name: Literal["x265"] = "x265"
    element: Literal["x265enc"] = "x265enc"
    format: ClassVar[str] = "I420"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "h265parse"
    options: Optional[str] = Field(
        label = "x265enc options",
        description = "Options for x265enc.",
        default = "key-int-max=25 speed-preset=veryfast tune=zerolatency",
        placeholder = "key-int-max=25 speed-preset=veryfast tune=zerolatency",
    )

class vah265encEncoderDTO(h265EncoderDTO):
    name: Literal["vah265enc"] = "vah265enc"
    element: Literal["vah265enc"] = "vah265enc"
    format: ClassVar[str] = "NV12"
    pre_elements: ClassVar[str] = "vapostproc"
    post_elements: ClassVar[str] = "h265parse"
    options: Optional[str] = Field(
        label = "vah265enc options",
        description = "Options for vah265enc.",
        default = "key-int-max=25",
        placeholder = "key-int-max=25",
    )

class vaapih265encEncoderDTO(h265EncoderDTO):
    name: Literal["vaapih265enc"] = "vaapih265enc"
    element: Literal["vaapih265enc"] = "vaapih265enc"
    format: ClassVar[str] = "NV12"
    pre_elements: ClassVar[str] = "vapostproc"
    post_elements: ClassVar[str] = "h265parse"
    options: Optional[str] = Field(
        label = "vaapih265enc options",
        description = "Options for vaapih265enc.",
        default = "keyframe-period=25",
        placeholder = "keyframe-period=25",
    )

class vulkanh265encEncoderDTO(h265EncoderDTO):
    name: Literal["vulkanh265enc"] = "vulkanh265enc"
    element: Literal["vulkanh265enc"] = "vulkanh265enc"
    format: ClassVar[str] = "NV12"
    pre_elements: ClassVar[str] = "vulkanupload"
    post_elements: ClassVar[str] = "h265parse"


class vp8EncoderDTO(videoEncoderDTO):
    codec: ClassVar[str] = "vp8"
    name: Literal["vp8enc"] = "vp8enc"
    element: Literal["vp8enc"] = "vp8enc"
    format: ClassVar[str] = "I420"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = ""
    options: Optional[str] = Field(
        label = "vp8enc options",
        description = "Options for vp8enc.",
        default = "deadline=1",
        placeholder = "deadline=1",
    )

class vp9EncoderDTO(videoEncoderDTO):
    codec: ClassVar[str] = "vp9"
    name: Literal["vp9enc"] = "vp9enc"
    element: Literal["vp9enc"] = "vp9enc"
    format: ClassVar[str] = "I420"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = ""
    options: Optional[str] = Field(
        label = "vp9enc options",
        description = "Options for vp9enc.",
        default = "deadline=1",
        placeholder = "deadline=1",
    )

class av1EncoderDTO(videoEncoderDTO):
    codec: ClassVar[str] = "av1"
    name: Literal["av1enc"] = "av1enc"
    element: Literal["av1enc"] = "av1enc"
    format: ClassVar[str] = "I420"
    pre_elements: ClassVar[str] = ""
    post_elements: ClassVar[str] = "av1parse"
    options: Optional[str] = Field(
        label = "av1enc options",
        description = "Options for av1enc (libaom).",
        default = "usage=realtime cpu-used=8",
        placeholder = "usage=realtime cpu-used=8",
    )


############################################################################

h264EncoderUnion = Annotated[
    Union[x264EncoderDTO, openh264EncoderDTO, vaapih264encEncoderDTO, vah264encEncoderDTO, vah264lpencEncoderDTO, mpph264encEncoderDTO, vulkanh264encEncoderDTO],
    Field(discriminator='name')
]

h265EncoderUnion = Annotated[
    Union[x265EncoderDTO, vah265encEncoderDTO, vaapih265encEncoderDTO, vulkanh265encEncoderDTO],
    Field(discriminator='name')
]
