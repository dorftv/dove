from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Union
from uuid import UUID
from api.encoder.video_encoder import h264EncoderUnion, h265EncoderUnion, x264EncoderDTO
from api.encoder.audio_encoder import aacEncoderDTO, mp2EncoderDTO, opusEncoderDTO
from api.encoder.mux import mpegtsMuxDTO
from event_loop_bridge import safe_broadcast
from api.helper import create_or_raise


router = APIRouter()

class rtspclientsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="RTSP Client Sink",
        default="rtspclientsink",
        description="stream output to RTSP Server.",
    )
    location: str = Field(
        label="location",
        title="Location",
        description="Location",
        placeholder="rtsp://server:port/path"
    )

    video_encoder: Union[UUID, h264EncoderUnion, h265EncoderUnion] = Field(
        default_factory=lambda: x264EncoderDTO(),
    )
    audio_encoder: Union[UUID, aacEncoderDTO, mp2EncoderDTO, opusEncoderDTO] = Field(
        default_factory=lambda: aacEncoderDTO(
            name="aac",
            options=""
        ),
    )
    mux: mpegtsMuxDTO = Field(
        default_factory=lambda: mpegtsMuxDTO(
            name = "mpegtsmux",
        ),
    )

from pipelines.outputs.rtspclientsink import rtspclientsinkOutput

@router.put("/rtspclientsink", response_model=SuccessDTO)
async def create_rtspclientsink_output(request: Request, data: rtspclientsinkOutputDTO):
    handler = request.app.state.pipeline_handler
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
        safe_broadcast("UPDATE", data)
    else:
        output = rtspclientsinkOutput(data=data)
        await create_or_raise(handler, output)

    return data