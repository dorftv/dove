from pydantic import BaseModel

class StatusDTO(BaseModel):
    message: str
