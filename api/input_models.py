from typing import Annotated, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


from config_handler import ConfigReader

from helpers import generateId, get_default_height, get_default_width

uniqueId = generateId("Input ")


class FilterDTO(BaseModel):
    """Base filter DTO — used for both audio and video filters."""
    type: str
    enabled: bool = True
    params: dict = {}

    def model_post_init(self, __context):
        for key, val in self.params.items():
            if isinstance(val, list) and len(val) == 1:
                self.params[key] = val[0]

# Aliases for clarity in type annotations
AudioFilterDTO = FilterDTO
VideoFilterDTO = FilterDTO


class InputDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    type: str
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "NEW"
    preview: Optional[bool] = True
    locked: Optional[bool] = False
    volume: Optional[float] = 0.8
    duration: Optional[int] = None
    position: Optional[int] = None
    details: Optional[str] = None
    buffering: Optional[int] = None
    show_controls: bool = True
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)
    has_video: Optional[bool] = Field(default_factory=lambda: ConfigReader().get_enable_video())
    has_audio: Optional[bool] = Field(default_factory=lambda: ConfigReader().get_enable_audio())
    fit: Optional[bool] = True  # True=maintain aspect ratio, False=stretch
    audio_filters: Optional[list[AudioFilterDTO]] = []
    video_filters: Optional[list[VideoFilterDTO]] = []

class updateInputDTO(BaseModel):
    uid: UUID
    type: str = 'update'
    name: Optional[str] = None
    position: Optional[int] = None
    state: Optional[str] = None
    volume: Optional[float] = None
    loop: Optional[bool] = None
    skip: Optional[str] = None
    fit: Optional[bool] = None
    audio_filters: Optional[list[AudioFilterDTO]] = None
    video_filters: Optional[list[VideoFilterDTO]] = None


class PositionDTO(BaseModel):
    uid: UUID
    position: int

class InputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    uid: UUID
