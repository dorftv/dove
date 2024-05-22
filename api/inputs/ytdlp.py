
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional

from api.websockets import manager
router = APIRouter()


class YtdlpInputDTO(InputDTO):
    type: str = Field(
        label="YtDlp",
        default="ytdlp",
        description="Allows playback from youtube and many other video sites.",
    )
    uri: str = Field(
        label="Uri",
        help="Any Url supported by youtube-dl fork ytdkp.",
        placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    loop: Optional[bool] = Field(
        label="Loop",
        defaut=False,
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