
import asyncio
from fastapi import APIRouter, Request, HTTPException
from api.input_models import InputDTO, SuccessDTO
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, validator

from helpers import get_default_height, get_default_width
from event_loop_bridge import safe_broadcast
from api.inputs.uridecodebin3 import check_uri_content_type
from api.helper import create_or_raise
router = APIRouter()



class PlaylistItemDTO(BaseModel):
    uri: str
    type: str
    name: Optional[str] = None
    duration: Optional[int] = None
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)

    @validator("type")
    @classmethod
    def valid_type(cls, value: str):
        ALLOWED_TYPES = ["video", "html"]
        if value not in ALLOWED_TYPES:
            raise ValueError(f"Invalid Playlist Item types, must be one of {', '.join(ALLOWED_TYPES)}")
        return value

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PlaylistInputDTO(InputDTO):
    type: str = Field(
        label="Playlists",
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
    current_clip: Optional[PlaylistItemDTO] = Field(
        label="current Clip",
        hidden=True,
        default=None,
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
    show_controls: bool = True





from pipelines.inputs.playlist import PlaylistInput

@router.put("/playlist", response_model=SuccessDTO)
async def create_playlist_input(request: Request, data: PlaylistInputDTO):
    if data.playlist:
        video_clips = [c for c in data.playlist if c.type == "video"]
        if video_clips:
            results = await asyncio.gather(
                *[check_uri_content_type(c.uri) for c in video_clips],
                return_exceptions=True
            )
            for clip, result in zip(video_clips, results):
                if isinstance(result, str):
                    raise HTTPException(422, f"Clip '{clip.uri}': {result}")

    handler = request.app.state.pipeline_handler
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = PlaylistInput(data=data)
        await create_or_raise(handler, input)

    return data