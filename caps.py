from typing import Optional

from pydantic import BaseModel


class Caps(BaseModel):
    video: Optional[str]
    audio: Optional[str]
