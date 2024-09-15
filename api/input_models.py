from typing import Annotated, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


from config_handler import ConfigReader

from helpers import generateId, get_default_height, get_default_width, get_default_volume

uniqueId = generateId("Input ")

class InputDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    type: str
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "NEW"
    height: Optional[int] = None
    width: Optional[int] = None
    preview: Optional[bool] = True
    locked: Optional[bool] = False
    volume: Optional[float] = 0.8
    duration: Optional[int] = None
    position: Optional[int] = None
    details: Optional[str] = None

class updateInputDTO(BaseModel):
    uid: UUID
    type: str = 'update'
    position: Optional[int] = None
    state: Optional[str] = None
    volume: Optional[float] = None
    loop: Optional[bool] = None


class PositionDTO(BaseModel):
    uid: UUID
    position: int

class InputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    uid: UUID
