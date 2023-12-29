from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo

from caps import Caps
from helpers import generateId

uniqueId = generateId("Output ")

class OutputDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    src: UUID
    type: str
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "PLAYING"
    height: Optional[int] = None
    width: Optional[int] = None
    volume: Optional[float] = 0.8

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str, info: FieldValidationInfo):
        ALLOWED_TYPES = ["preview_hls"]
        if value not in ALLOWED_TYPES:
            raise ValueError(f"Invalid input types, must be one of {', '.join(ALLOWED_TYPES)}")

        return value

    @field_validator("state")
    @classmethod
    def valid_state(cls, value: str, info: FieldValidationInfo):
        ALLOWED_STATES = ["PLAYING", "READY"]
        if value not in ALLOWED_STATES:
            raise ValueError(f"Invalid state, must be one of {', '.join(ALLOWED_STATES)}")

        return value

# @TODO use default from config file
class previewHlsOutputDTO(OutputDTO):
    type: str = "preview_hls"
    height: Optional[int] = 180
    width: Optional[int] = 320



class OutputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    code: int
    details: str
