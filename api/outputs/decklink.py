from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional

from api.websockets import manager


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
    interlaced: bool = Field(
        label="Interlaces",
        defaut=False,
        help="Interlace the output.",
    )


from pipelines.outputs.decklink import DecklinkOutput

@router.put("/decklink", response_model=SuccessDTO)
async def create_srtsink_output(request: Request, data: DecklinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = DecklinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data