from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from config_handler import ConfigReader

from caps import Caps
from helpers import generateId

config = ConfigReader()

uniqueId = generateId("Output ")

def get_default_height() -> int:
    return config.get_default_resolution()['height']

def get_default_width() -> int:
    return config.get_default_resolution()['width']

def get_default_volume() -> int:
    return config.get_default_volume()
# @TODO use default from config file


class OutputDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    src: UUID
    type: str
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "PLAYING"
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)
    locked: Optional[bool] = False
    details: Optional[str] = None

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str, info: FieldValidationInfo):
        ALLOWED_TYPES = ["preview_hls", "srtsink", "decklinksink"]
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


class previewHlsOutputDTO(OutputDTO):
    type: str = "preview_hls"
    height: Optional[int] = 180
    width: Optional[int] = 320

class fakeOutputDTO(OutputDTO):
    type: str = "fakesink"

# @TODO add encoder options
class srtOutputDTO(OutputDTO):
    type: str = "srtsink"
    uri: str
    streamid: Optional[str] = ''

class decklinkOutputDTO(OutputDTO):
    type: str = "decklinksink"
    device: int
    mode: int
    interlaced: bool

class shout2sendOutputDTO(OutputDTO):
    type: str = "shout2send"
    mount: str
    ip: str
    port: int
    username: str
    password: str

class OutputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    code: int
    details: str
