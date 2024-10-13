from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional,  Literal, Union
from api.encoder.video_encoder import h264EncoderUnion, h265EncoderUnion, x264EncoderDTO
from api.encoder.audio_encoder import aacEncoderDTO, mp2EncoderDTO, opusEncoderDTO
from api.encoder.mux import mpegtsMuxDTO
from api.websockets import manager



router = APIRouter()

# @TODO improve codec handling
class rtspclientsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="SRT Sink",
        default="rtspclientsink",
        description="stream output to SRT Server.",
    )
    location: str = Field(
        label="location",
        title="Location",
        description="Location",
        placeholder="api/outputs/rtspclientsink.py"
    )

    video_encoder: Union[h264EncoderUnion, h265EncoderUnion] = Field(
        default_factory=lambda: x264EncoderDTO(),
    )
    audio_encoder: Union[aacEncoderDTO, mp2EncoderDTO, opusEncoderDTO] = Field(
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
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = rtspclientsinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data