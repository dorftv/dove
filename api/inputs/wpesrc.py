
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from api.websockets import manager
router = APIRouter()


class WpesrcInputDTO(InputDTO):
    type: str =  Field(
        label="HTML/Websites",
        default="wpesrc",
        description="Wpesrc allows rendering HTML.",
    )
    location: Optional[str] =  Field(
        label="Location",
        placeholder="https://dorftv.at",
        description="Enter the location of the HTML source.",
        help="file:// or http://"
    )
    draw_background: Optional[bool] = Field(
        label="Draw Background",
        default=False,
        help="use transparent background when not set."
    )
    show_controls: bool = False


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
