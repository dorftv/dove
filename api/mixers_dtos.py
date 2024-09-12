from typing import Annotated, Optional, List
from uuid import UUID, uuid4
from typing import Union, Literal

from pydantic import BaseModel, Field, field_validator, validator, model_validator, root_validator, PrivateAttr
from pydantic_core.core_schema import FieldValidationInfo
from helpers import generateId, get_default_height, get_default_width, get_default_volume
from config_handler import ConfigReader


config = ConfigReader()

uniqueId = generateId("Scene ")
uniqueIntId = generateId()

class mixerInputDTO(BaseModel):
    index: Optional[int] = None
    name: Optional[str] = None
    sink: Optional[str] = None
    src: Union[UUID, str] = "None"
    xpos: Optional[int] = 0
    ypos: Optional[int] = 0
    width: Optional[int] = None
    height: Optional[int] = None
    alpha: Optional[float] = 1
    zorder: Optional[int] = None
    volume: Optional[float] = 1
    mute: Optional[bool] = False
    locked: Optional[bool] = False
    src_locked: Optional[bool] = False


class mixerInputsDTO(BaseModel):
    src: UUID
    #src: Optional[List[mixerInputDTO]] = []


class mixerBaseDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    #sources:  Optional[List[mixerInputDTO]] = Field(default_factory=list)
    sources: Optional[List[mixerInputDTO]] = []

    preview: Optional[bool] = True
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "PLAYING"
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)
    volume: Optional[float] = Field(default_factory=get_default_volume)
    details: Optional[str] = None

    def add_slot(self, source: mixerInputDTO = None):
        if source == None:
            source = mixerInputDTO()
        source.index = len(self.sources)
        self.sources.append(source)
        data = dict(source)
        data.pop('index', None)
        self.update_mixer_input(source.index, **data)
        self.update_source_with_defaults(source.index)


    def remove_slot(self, source: mixerInputDTO):
        if source in self.sources:
            self.sources.remove(source)
            self._reindex_sources()

    def _reindex_sources(self):
        for i, source in enumerate(self.sources):
            source.index = i

    def addInput(self, src: mixerInputDTO):
        if not any(source.sink == src.sink for source in self.sources):
            self.sources.append(src)

    def getMixerInputDTO(self, index: int):
        for source in self.sources:
            if source.index ==  index:
                return source
        return None

    def update_source_with_defaults(self, index: int):
        for source in self.sources:
            if source.index == index:
                if source.width is None:
                    source.width = self.width
                if source.height is None:
                    source.height = self.height
                if source.zorder is None:
                    source.zorder = source.index + 2
                if source.name is None:
                    source.name = f"Slot {source.index}"
                break

    def update_mixer_input(self, index: int, **kwargs):
        for source in self.sources:
            if source.index == index:
                for key, value in kwargs.items():
                    if key == "alpha":
                        value = float(value)
                    setattr(source, key, value)
                break

class mixerDTO(mixerBaseDTO):
    type: Optional[str] = "mixer"
    sources:  Optional[List[mixerInputDTO]] = Field(default_factory=list)


class sceneMixerDTO(mixerBaseDTO):
    type: Optional[str] = "scene"
    n: Optional[int] = 0
    locked: Optional[bool] = False
    src_locked: Optional[bool] = False



    def getMixerInputN(self, n):
        return self.sources[n] if len(self.sources) > n else None

    def countMixerInputs(self):
        return len(self.sources) if self.sources else None



    def getMixerInputDTObySource(self, src: UUID):
        for source in self.sources:
            if str(source.src) == str(src):
                return source



    def removeInput(self, sink):
        self.sources = [source for source in self.sources if source.sink != sink]



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
    active: Optional[int] = None

class MixerDeleteDTO(BaseModel):
    uid: UUID

class mixerRemoveSlotDTO(BaseModel):
    uid: UUID
    index: Optional[int] = None

class mixerSlotDTO(BaseModel):
    uid: UUID
    slot:  Optional[mixerInputDTO] = None

class mixerCutDTO(BaseModel):
    src: Union[UUID, str] = "None"
    target: UUID
    index: Optional[int] = None

class mixerCutProgramDTO(BaseModel):
    src: Union[UUID, str] = "None"
    transition: Optional[str] = None
    duration: Optional[int] = None


class mixerRemoveDTO(BaseModel):
    src: UUID
    index: Optional[int] = None

class SuccessDTO(BaseModel):
    code: int
    details: str