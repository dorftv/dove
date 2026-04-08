
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, SuccessDTO
from typing import Optional

from event_loop_bridge import safe_broadcast
router = APIRouter()


class CefsrcInputDTO(InputDTO):
    type: str = Field(
        label="HTML/CEF",
        default="cefsrc",
        description="CEF (Chromium Embedded Framework) allows rendering HTML.",
    )
    url: Optional[str] = Field(
        label="URL",
        placeholder="https://dorftv.at",
        description="Enter the URL of the HTML source.",
        help="file:// or http://"
    )
    show_controls: bool = False


from pipelines.inputs.cefsrc import CefsrcInput

@router.put("/cefsrc", response_model=SuccessDTO)
async def create_cefsrc_input(request: Request, data: CefsrcInputDTO):
    handler = request.app.state.pipeline_handler
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = CefsrcInput(data=data)
        handler.add_pipeline(input)

    return data
