
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional

from api.websockets import manager
router = APIRouter()

# @TODO move receiving url here, and use playbin input class
class YtdlpInputDTO(InputDTO):
    type: str = Field(
        label="Youtube&Co",
        default="ytdlp",
        description="Allows playback from youtube and many other video sites supported by yt-dlp.",
    )
    uri: str = Field(
        label="Uri",
        help="Any Url supported by youtube-dl fork yt-dlp.",
        placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    loop: Optional[bool] = Field(
        label="Loop",
        default=False,
        help="Loop the the file on EOS"
    )

from pipelines.inputs.ytdlp import YtdlpInput

@router.put("/ytdlp", response_model=SuccessDTO)
async def create_ytdlp_input(request: Request, data: YtdlpInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
    else:
        input = YtdlpInput(data=data)
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data