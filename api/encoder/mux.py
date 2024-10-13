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
