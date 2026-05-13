from fastapi import APIRouter, Request
from pydantic import Field
from dove.api.output_models import OutputDTO, SuccessDTO
from typing import Optional

from dove.event_loop_bridge import safe_broadcast
from dove.api.helper import create_or_raise


router = APIRouter()


class DecklinkOutputDTO(OutputDTO):
    type: str = Field(
        label="Decklink",
        default="decklink",
        description="Outputs to decklink family video cards."
    )
    device: int =  Field(
        label="Device",
        description="Device ID",
        help="The device ID of the decklink device to output to.",
        placeholder="1",
    )
    mode: int =  Field(
        label="Mode",
        description="Output Mode",
        help="The output Mode to use. eg. 43 for PAL Widescreen",
        placeholder="43",
    )
    interlaced: Optional[bool] = Field(
        label="Interlaces",
        default=False,
        help="Interlace the output.",
    )


from dove.pipelines.outputs.decklink import DecklinkOutput

@router.put("/decklink", response_model=SuccessDTO)
async def create_decklink_output(request: Request, data: DecklinkOutputDTO):
    handler = request.app.state.pipeline_handler
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
        safe_broadcast("UPDATE", data)
    else:
        output = DecklinkOutput(data=data)
        await create_or_raise(handler, output)

    return data