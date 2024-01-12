from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo

from caps import Caps
from helpers import generateId
from config_handler import ConfigReader  

config = ConfigReader('/app/config.toml')

# @TODO add function that returns dict of DTOS for using in api
# see get_field_requirements(model)
# type: DTO
# eg: urisrc: UriInputDTO

uniqueId = generateId("Input ")

def get_default_height() -> int:
    return config.get_default_resolution()['height']

def get_default_width() -> int:
    return config.get_default_resolution()['width']

class InputDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    name: str = Field(default_factory=lambda: next(uniqueId))
    type: str
    state: Optional[str] = "PLAYING"
    height: Optional[int] = None
    width: Optional[int] = None
    preview: Optional[bool] = True
    volume: Optional[float] = 0.8

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str, info: FieldValidationInfo):
        ALLOWED_TYPES = ["testsrc", "urisrc", "wpesrc", "ytdlpsrc"]
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

    def get_field_requirements(model):
        schema = model.schema()
        fields = schema.get('properties', {})
        field_requirements = [
            {"name": field_name, "type": field_info.get('type'), "required": field_name in schema.get('required', [])}
            for field_name, field_info in fields.items()
        ]
        return field_requirements

class TestInputDTO(InputDTO):
    type: str = "testsrc"
    pattern: Optional[int] = 1
    wave: Optional[int] = 1
    freq: Optional[float] = 440.0
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)

class UriInputDTO(InputDTO):
    type: str = "urisrc"
    uri: str
    loop: Optional[bool] = False

class ytDlpInputDTO(InputDTO):
    type: str = "ytdlpsrc"
    uri: str
    loop: Optional[bool] = False

class WpeInputDTO(InputDTO):
    type: str = "wpesrc"
    location: Optional[str] = "https://dorftv.at"
    draw_background: Optional[bool] = False
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)


class PlaylistInputDTO(InputDTO):
    playlist_uri: Optional[str] = None
    playlist: Optional[list] = None
    next: Optional[dict] = None
    looping: bool = False

class InputDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    code: int
    details: str
