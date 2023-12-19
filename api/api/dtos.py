from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo

from caps import Caps

class InputDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    type: str
    name: Optional[str] = None
    state: Optional[str] = "PLAYING"
    height: Optional[int] = None
    width: Optional[int] = None
    preview: Optional[bool] = True
    
    # optional inputs for some inputs
    # TODO validate
    
    # test_input
    pattern: Optional[int] = 0
    volume: Optional[float] = 0.8
    wave: Optional[int] = 1
    freq: Optional[float] = 440.0
    
    # uri input
    uri: Optional[str] = None

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str, info: FieldValidationInfo):
        ALLOWED_TYPES = ["testsrc", "uri"]
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

class InputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    code: int
    details: str
