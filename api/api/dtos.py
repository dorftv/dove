from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo

from caps import Caps

class InputDTO(BaseModel):
    type: str
    uid: Annotated[UUID, Field(default=uuid4())]
    caps: Caps
    attrs: dict

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str, info: FieldValidationInfo):
        ALLOWED_TYPES = ["TestInput", "URIInput"]
        if value not in ALLOWED_TYPES:
            raise ValueError(f"Invalid input types, must be one of {', '.join(ALLOWED_TYPES)}")

        return value

class InputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    code: int
    details: str
