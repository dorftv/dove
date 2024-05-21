
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from api.websockets import manager
router = APIRouter()


class WpesrcInputDTO(InputDTO):
    type: str = "wpesrc"
    location: Optional[str] = "https://dorftv.at"
    draw_background: Optional[bool] = False
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)

from pipelines.inputs.wpesrc import WpesrcInput

@router.put("/wpesrc", response_model=SuccessDTO)
async def create_wpesrc_input(request: Request, data: WpesrcInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
    else:
        input = WpesrcInput(data=data)
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data