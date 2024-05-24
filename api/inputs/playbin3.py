
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional

from api.websockets import manager
router = APIRouter()


class Playbin3InputDTO(InputDTO):
    type: str =  Field(
        label="Playbin3",
        default="playbin3",
        description="Playbin3 plays local and remote files and streams.",
    )
    uri: str = Field(
        label="Uri",
        description="Enter Uri to play",
        help="eg: file:/// | http://  | rtmp:// | srt://",
        placeholder="file:///home/user/video.mp4",
    )
    loop: Optional[bool] = Field(
        label="Loop",
        default=False,
        help="Loop the the file on EOS"
    )


from pipelines.inputs.playbin3 import Playbin3Input

@router.put("/playbin3", response_model=SuccessDTO)
async def create_playbin3_input(request: Request, data: Playbin3InputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
    else:
        input = Playbin3Input(data=data)
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data