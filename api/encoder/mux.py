from typing import Annotated, Optional, Literal, Union
from pydantic import  Field

from .encoder import EncoderDTO

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

class webmMuxDTO(muxDTO):
    name: Literal["webmmux"] = "webmmux"
    element: Literal["webmmux"] = "webmmux"
    options: Optional[str] = Field(
        label = "WebM mux options",
        description = "Options for webmmux.",
        default = "",
        placeholder = "",
    )

class matroskaMuxDTO(muxDTO):
    name: Literal["matroskamux"] = "matroskamux"
    element: Literal["matroskamux"] = "matroskamux"
    options: Optional[str] = Field(
        label = "Matroska mux options",
        description = "Options for matroskamux.",
        default = "",
        placeholder = "",
    )

class mp4MuxDTO(muxDTO):
    name: Literal["mp4mux"] = "mp4mux"
    element: Literal["mp4mux"] = "mp4mux"
    options: Optional[str] = Field(
        label = "MP4 mux options",
        description = "Options for mp4mux.",
        default = "fragment-duration=1000",
        placeholder = "fragment-duration=1000",
    )

class oggMuxDTO(muxDTO):
    name: Literal["oggmux"] = "oggmux"
    element: Literal["oggmux"] = "oggmux"
    options: Optional[str] = Field(
        label = "Ogg mux options",
        description = "Options for oggmux.",
        default = "",
        placeholder = "",
    )
