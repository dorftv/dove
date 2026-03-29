
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional

from event_loop_bridge import safe_broadcast
from api.helper import create_or_raise
router = APIRouter()

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
    handler = request.app.state.pipeline_handler
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = YtdlpInput(data=data)
        await create_or_raise(handler, input)

    return data