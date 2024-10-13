from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional, Literal, Union
from api.encoder.video_encoder import h264EncoderUnion, x264EncoderDTO
from api.encoder.audio_encoder import aacEncoderDTO, mp3EncoderDTO
from api.encoder.mux import flvMuxDTO
from api.websockets import manager



router = APIRouter()


class rtmpsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="RTMP Sink",
        default="rtmpsink",
        description="stream output to RTMP Server.",
    )
    uri: str = Field(
        label="Uri",
        description="Enter RTMP Server URL and Port",
        placeholder="rtmp://server:port/myapp/mystream"
    )

    video_encoder: h264EncoderUnion = Field(
        default_factory=lambda: x264EncoderDTO(
            options="tune=zerolatency pass=cbr bitrate=8192",
            profile="baseline",
        )
    )
    audio_encoder: Union[aacEncoderDTO] = Field(
        default_factory=lambda: aacEncoderDTO(
            name="aac",
            options=""
        )
    )
    mux:flvMuxDTO = Field(
        default_factory=lambda: flvMuxDTO(
            name = "flvmux",
            element = "flvmux",
            options=""
        )
    )

from pipelines.outputs.rtmpsink import rtmpsinkOutput

@router.put("/rtmpsink", response_model=SuccessDTO)
async def create_rtmpsink_output(request: Request, data: rtmpsinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = RtmpsinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data