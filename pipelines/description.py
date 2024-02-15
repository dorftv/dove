from uuid import UUID

from pydantic import BaseModel


class Description(BaseModel):
    uid: UUID
    attrs: dict
