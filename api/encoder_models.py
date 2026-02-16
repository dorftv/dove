from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from helpers import generateId
from api.input_models import AudioFilterDTO

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
    # Per-encoder audio filter chain (audio encoders only). Lets production encoders
    # apply loudness normalization without affecting the live preview path.
    audio_filters: Optional[list[AudioFilterDTO]] = []
    # Video encoders only — auto-synced to match the longest audio filter latency
    # on the same source (so A/V stays in sync on the encoded output).
    video_delay_ms: Optional[int] = 0


class EncoderUpdateDTO(BaseModel):
    uid: UUID
    name: Optional[str] = None
    audio_filters: Optional[list[AudioFilterDTO]] = None


class EncoderEntityDeleteDTO(BaseModel):
    uid: UUID
