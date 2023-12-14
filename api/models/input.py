from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

class InputTypes(str, Enum):
    test_src = "test_src"
    uri = "uri"
    playlist = "playlist"

class Description(BaseModel):
    uid: UUID

class InputDTO(BaseModel):
    uid: UUID

class InputCreateDTO(InputDTO):
    type: Optional[InputTypes] = None
    name: str
    state: str
    height: int
    width: int
    preview: bool

class OutputDTO(BaseModel):
    uid: UUID
    state: str