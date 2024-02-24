from typing import Annotated, Optional, List
from uuid import UUID, uuid4
from typing import Union, Literal

from pydantic import BaseModel, Field, field_validator, validator, model_validator, root_validator
from pydantic_core.core_schema import FieldValidationInfo
from helpers import generateId
from config_handler import ConfigReader  

config = ConfigReader()

uniqueId = generateId("Mixer ")
uniqueIntId = generateId()


class mixerInputDTO(BaseModel):
    index: int =  Field(default_factory=lambda: int(next(uniqueIntId)))
    name: Optional[str] = None
    sink: Optional[str] = None
    src: Union[UUID, str] = "None"
    xpos: Optional[int] = 0
    ypos: Optional[int] = 0
    width: Optional[int] = None
    height: Optional[int] = None
    alpha: Optional[float] = 1
    zorder: Optional[int] = None
    volume: Optional[int] = 1
    locked: Optional[bool] = False
    src_locked: Optional[bool] = False


class mixerInputsDTO(BaseModel):
    src: UUID
    #src: Optional[List[mixerInputDTO]] = []

def get_default_height() -> int:
    return config.get_default_resolution()['height']

def get_default_width() -> int:
    return config.get_default_resolution()['width']

def get_default_volume() -> int:
    return config.get_default_volume()

class mixerBaseDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    preview: Optional[bool] = True
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "PLAYING"
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)
    volume: Optional[float] = Field(default_factory=get_default_volume)

class mixerDTO(mixerBaseDTO):
    type: Optional[str] = "mixer"    
    sources:  Optional[List[mixerInputDTO]] = Field(default_factory=list)


class sceneMixerDTO(mixerBaseDTO):
    type: Optional[str] = "scene"
    sources:  Optional[List[mixerInputDTO]] = Field(default_factory=list)
    n: Optional[int] = 0
    locked: Optional[bool] = False

    def update_sources_with_defaults(self):
        for source in self.sources:
            if source.width is None:
                source.width = self.width
            if source.height is None:
                source.height = self.height

    def getMixerInputN(self, n):
        return self.sources[n] if len(self.sources) > n else None

    def countMixerInputs(self):
        return len(self.sources) if self.sources else None

    def getMixerInputDTO(self, sink: str):
        for source in self.sources:
            if (str(source.sink)) ==  (str(sink)):
                return source
        return None

    def getMixerInputDTObySource(self, src: UUID):
        for source in self.sources:
            print(source.src)
            if str(source.src) == str(src):
                return source

    def addInput(self, src: mixerInputDTO):
        if not any(source.sink == src.sink for source in self.sources):
            self.sources.append(src)

    def removeInput(self, sink):
        self.sources = [source for source in self.sources if source.sink != sink]

    def update_mixer_input(self, sink: str, **kwargs):
        updatedSources = []
        for source in self.sources:
            if str(source.sink) == str(sink):
                for key, value in kwargs.items():
                    setattr(source, key, value)
            updatedSources.append(source)
        self.sources = updatedSources

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str, info: FieldValidationInfo):
        ALLOWED_TYPES = ["scene", "program", "preview"]
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


class programMixerDTO(mixerBaseDTO):
    type: str = "program"
    sink_1: Optional[UUID] = None
    sink_2: Optional[UUID] = None
    active: Optional[str] = "sink_1"
    transition: Optional[str] = None

class previewMixerDTO(mixerBaseDTO):
    type: str = "preview"
    src: Optional[UUID] = None

class MixerDeleteDTO(BaseModel):
    uid: UUID

class mixerPadDTO(BaseModel):
    uid: UUID
    sink: Optional[mixerInputDTO] = None

class mixerCutDTO(BaseModel):
    src: Union[UUID, str] = "None"
    target: UUID
    sink: Optional[str] = None

class mixerRemoveDTO(BaseModel):
    src: UUID
    sink: Optional[str] = None

class SuccessDTO(BaseModel):
    code: int
    details: str