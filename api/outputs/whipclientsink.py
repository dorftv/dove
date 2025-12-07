from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Union
from uuid import UUID
from api.encoder.video_encoder import h264EncoderUnion, x264EncoderDTO
from event_loop_bridge import safe_broadcast


router = APIRouter()


class whipclientsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="Whip Client Sink",
        default="whipclientsink",
        description="stream output to a WHIP server.",
    )
    whip_endpoint: str = Field(
        label="WHIP Endpoint",
        description="WHIP server endpoint URL",
        placeholder="http://mediamtx:8889/stream/whip"
    )
    video_encoder: Union[UUID, h264EncoderUnion] = Field(
        default_factory=lambda: x264EncoderDTO(),
    )

from pipelines.outputs.whipclientsink import whipclientsinkOutput

@router.put("/whipclientsink", response_model=SuccessDTO)
async def create_whipclientsink_output(request: Request, data: whipclientsinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
        safe_broadcast("UPDATE", data)
    else:
        output = whipclientsinkOutput(data=data)
        handler.add_pipeline(output)

    return data
