
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from event_loop_bridge import safe_broadcast
router = APIRouter()


class WhipInputDTO(InputDTO):
    type: str = Field(
        label="Screencast",
        default="whip",
        description="WebRTC ingest via WHIP (screen sharing, camera).",
    )
    show_controls: bool = False
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)

from pipelines.inputs.whip import WhipInput

@router.put("/whip", response_model=SuccessDTO)
async def create_whip_input(request: Request, data: WhipInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = WhipInput(data=data)
        handler.add_pipeline(input)

    return data
