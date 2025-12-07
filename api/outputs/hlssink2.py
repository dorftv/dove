from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional
from event_loop_bridge import safe_broadcast



router = APIRouter()


class hlssink2OutputDTO(OutputDTO):
    type: str = Field(
        label="HLS Sink",
        default="hlssink2",
        description="stream output to HLS.",
    )

@router.put("/hlssink2", response_model=SuccessDTO)
async def create_hlssink2_output(request: Request, data: hlssink2OutputDTO):
    from pipelines.outputs.hlssink2 import hlssink2Output
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
        safe_broadcast("UPDATE", data)
    else:
        output = hlssink2Output(data=data)
        handler.add_pipeline(output)

    return data