from typing import Annotated, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo

from caps import Caps

# @TODO add function that returns dict of DTOS for using in api
# see get_field_requirements(model)
# type: DTO
# eg: urisrc: UriInputDTO


class mixerDTO(BaseModel):
    src: UUID
    target: UUID
