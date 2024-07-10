
from fastapi import APIRouter, Request
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional, List
from pydantic import BaseModel, Field, validator

from api.websockets import manager
router = APIRouter()


class PlaylistItemDTO(BaseModel):
    uri: str
    type: str
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

    @validator("type")
    @classmethod
    def valid_type(cls, value: str):
        ALLOWED_TYPES = ["video", "html"]
        if value not in ALLOWED_TYPES:
            raise ValueError(f"Invalid Playlist Item types, must be one of {', '.join(ALLOWED_TYPES)}")
        return value

    class Config:
        arbitrary_types_allowed = True


class PlaylistInputDTO(InputDTO):
    type: str = Field(
        label="Playlist",
        default="playlist",
        description="Provide an URL to fetch a JSON Playlist.",
    )
    next: Optional[str] = Field(
        label="Playlist URL",
        default=None,
        description="Loads playlist from URL when playlist is empty or finished.",
    )
    index: int = Field(
        label="Index",
        hidden=True,
        default=0,
        description="Current.",
    )
    current_clip: Optional[PlaylistItemDTO] =  Field(
        label="current Clip",
        hidden=True,
        default=0,
        description="Current Clip.",
    )
    looping: bool = Field(
        label="Looping",
        default=False,
        description="Loop the playlist when finished.",
    )
    total_duration: Optional[int] =Field(
        label="Total Duration Clip",
        hidden=True,
        default=None,
    )
    total_position: Optional[int] =Field(
        label="Total Duration Clip",
        hidden=True,
        default=None,
    )
    playlist:  Optional[List[PlaylistItemDTO]] = Field(
        label="Playlist Items",
        hidden=True,
        default_factory=list
    )




from pipelines.inputs.playlist import PlaylistInput

@router.put("/playlist", response_model=SuccessDTO)
async def create_playlist_input(request: Request, data: PlaylistInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
    else:
        input = PlaylistInput(data=data)
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data