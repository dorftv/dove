from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from helpers import generateId

uniqueId = generateId("Encoder ")


class EncoderEntityDTO(BaseModel):
    uid: Optional[UUID] = Field(default_factory=uuid4)
    name: str = Field(default_factory=lambda: next(uniqueId))
    type: str = Field(description="video or audio")
    src: Optional[UUID] = None
    element: str = ""
    options: str = ""
    codec: str = ""
    # Video-specific
    width: Optional[int] = None
    height: Optional[int] = None
    framerate: Optional[str] = None
    profile: Optional[str] = None
    # State
    state: str = "PENDING"
    is_preview: bool = False
    details: Optional[str] = None


class EncoderEntityDeleteDTO(BaseModel):
    uid: UUID
