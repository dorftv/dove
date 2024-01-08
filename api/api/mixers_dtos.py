from typing import Annotated, Optional, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, validator, model_validator, root_validator
from pydantic_core.core_schema import FieldValidationInfo
from caps import Caps
from helpers import generateId
from config_handler import ConfigReader  

config = ConfigReader('/app/config.toml')

uniqueId = generateId("Mixer ")

class mixerInputDTO(BaseModel):
    src: UUID
    sink: Optional[str] = None
    xpos: Optional[int] = None
    ypos: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    alpha: Optional[float] = None
    zorder: Optional[int] = None
    immutable: Optional[bool] = False

class mixerInputsDTO(BaseModel):
    src: UUID
    #src: Optional[List[mixerInputDTO]] = []

def get_default_height() -> int:
    return config.get_default_resolution()['height']

def get_default_width() -> int:
    return config.get_default_resolution()['width']

def get_default_volume() -> int:
    return config.get_default_volume()

class mixerDTO(BaseModel):
    uid: Annotated[Optional[UUID], Field(default_factory=lambda: uuid4())]
    sources:  Optional[List[mixerInputDTO]] = Field(default_factory=list)
    type: Optional[str] = "mixer"
    preview: Optional[bool] = True
    name: str = Field(default_factory=lambda: next(uniqueId))
    state: Optional[str] = "PLAYING"
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)
    volume: Optional[float] = Field(default_factory=get_default_volume)

    # remove all sources but src
    def cut_source(self, src: UUID):
        if not any(source.src == src for source in self.sources):
            self.sources.append(mixerInputDTO(src=src))
            self.sources = [source for source in self.sources if source.src == src]
            return True

        self.sources = [source for source in self.sources if source.src == src]
        return False
    
    # add src to mixer
    def overlay_source(self, src: UUID):
        new_source = mixerInputDTO(src=src)

        if not any(source.src == new_source.src for source in self.sources):
            self.sources.append(new_source)

    def remove_source(self, src: UUID):
        index_to_remove = next((i for i, source in enumerate(self.sources) if source.src == src), None)
        if index_to_remove is not None:
            self.sources.pop(index_to_remove)
        
    def update_or_set_mix(self, new_mix_dto: mixerInputDTO):
        if self.mix is None or self.mix.target != new_mix_dto.target:
            # If there is no existing mix, or the target UID doesn't match, set the new mixerInputsDTO
            self.mix = new_mix_dto
        else:
            # If the target UID matches, update the existing mix
            self.mix.src = new_mix_dto.src

    def update_mixer_input(self, src: UUID, **kwargs):
        updatedSources = []
        for source in self.sources:
            if UUID(str(source.src)) ==  UUID(str(src)):
                for key, value in kwargs.items():
                    setattr(source, key, value)
            updatedSources.append(source)
        self.sources = updatedSources

    def get_mixer_input(self, src: UUID):
        for source in self.sources:
            if UUID(str(source.src)) ==  UUID(str(src)):
                return source

    @field_validator("type")
    @classmethod
    def valid_type(cls, value: str, info: FieldValidationInfo):
        ALLOWED_TYPES = ["mixer", "program", "preview"]
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


class mixerCutDTO(BaseModel):
    src: UUID
    target: UUID

class mixerRemoveDTO(BaseModel):
    src: UUID




# @TODO use default from config file
# used for preview and program
class mixerMixerDTO(mixerDTO):
    type: Optional[str] = "mixer"



# @TODO use default from config file
# used for preview and program
class outputMixerDTO(mixerDTO):
    type: str




class MixerDeleteDTO(BaseModel):
    uid: UUID

class SuccessDTO(BaseModel):
    code: int
    details: str
