from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Literal, Union, Optional
from api.encoder.video_encoder import h264EncoderUnion, x264EncoderDTO
from api.encoder.audio_encoder import  aacEncoderDTO, mp2EncoderDTO
from api.websockets import manager



router = APIRouter()


class hlssink2OutputDTO(OutputDTO):
    type: str = Field(
        label="HLS Sink",
        default="hlssink2",
        description="stream output to HLS.",
    )
    video_encoder: h264EncoderUnion = Field(
        default_factory=lambda: x264EncoderDTO(
            options="key-int-max=30  speed-preset=ultrafast",
            profile="main",
        )
    )
    audio_encoder: Union[aacEncoderDTO] = Field(
        default_factory=lambda: aacEncoderDTO(
            name="aac",
            options=""
        )
    )

from pipelines.outputs.hlssink2 import hlssink2Output

@router.put("/hlssink2", response_model=SuccessDTO)
async def create_rtmpsink_output(request: Request, data: hlssink2OutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = hlssink2Output(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data