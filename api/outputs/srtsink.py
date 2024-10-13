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
class srtsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="SRT Sink",
        default="srtsink",
        description="stream output to SRT Server.",
    )
    uri: str = Field(
        label="Uri",
        title="Uri",
        description="Enter SRT Server URL and Port",
        placeholder="srt://server:port"
    )

    streamid: Optional[str] = Field(
        default=None,
        label="Stream ID",
        description="Optional stream identifier",
        placeholder="streamid"
    )
    video_encoder: Union[h264EncoderUnion, h265EncoderUnion] = Field(
        default_factory=lambda: x264EncoderDTO(options="key-int-max=30 speed-preset=veryfast")
    )
    audio_encoder: Union[aacEncoderDTO, mp2EncoderDTO, opusEncoderDTO] = Field(
        default_factory=lambda: aacEncoderDTO()
    )
    mux: mpegtsMuxDTO = Field(
        default_factory=lambda: mpegtsMuxDTO(
            name = "mpegtsmux",
            options="alignment=7"
        ),
    )

from pipelines.outputs.srtsink import srtsinkOutput

@router.put("/srtsink", response_model=SuccessDTO)
async def create_srtsink_output(request: Request, data: srtsinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = srtsinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data