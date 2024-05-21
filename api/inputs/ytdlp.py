
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional

from api.websockets import manager
router = APIRouter()


class YtdlpInputDTO(InputDTO):
    type: str = "ytdlp"
    uri: str
    loop: Optional[bool] = False

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