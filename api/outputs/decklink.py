from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional

from api.websockets import manager



router = APIRouter()



class DecklinkOutputDTO(OutputDTO):
    type: str = "decklink"
    device: int
    mode: int
    interlaced: bool


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