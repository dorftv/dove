from pydantic import BaseModel
from typing import Annotated
from uuid import UUID

class PositionDTO(BaseModel):
    uid: UUID
    position: int
