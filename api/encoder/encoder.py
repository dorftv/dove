from typing import Annotated, Optional, Literal, Union
from pydantic import BaseModel, Field

class EncoderDTO(BaseModel):
    name: str
    options: Optional[str] = Field(
        label = "Options",
        description = "Options",
        default = "",
        placeholder =  ""
    )
