from typing import Annotated, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field



from dove.helpers import generateId, get_default_height, get_default_width, get_default_framerate

uniqueId = generateId("Output ")

class OutputDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    src: Optional[UUID] = None
    type: str
    is_preview: Optional[bool] = False
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "PLAYING"
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)
    framerate: Optional[str] = Field(default_factory=get_default_framerate)
    locked: Optional[bool] = False
    details: Optional[str] = None
    stats: Optional[dict] = None
    video_encoder: Optional[UUID] = None
    audio_encoder: Optional[UUID] = None


class OutputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    uid: UUID
