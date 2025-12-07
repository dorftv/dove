from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional, Union
from uuid import UUID
from api.encoder.video_encoder import h264EncoderUnion, h265EncoderUnion, x264EncoderDTO
from api.encoder.audio_encoder import aacEncoderDTO, mp2EncoderDTO
from api.encoder.mux import mpegtsMuxDTO
from event_loop_bridge import safe_broadcast


router = APIRouter()

class SrtserversinkOutputDTO(OutputDTO):
    type: str = Field(
        label="SRT Server Sink",
        default="srtserversink",
        description="SRT listener — clients connect to this output.",
    )
    uri: str = Field(
        label="Uri",
        description="Listening address and port",
        placeholder="srt://0.0.0.0:7777"
    )
    latency: Optional[int] = Field(
        label="latency",
        default=400,
        description="Latency for SRT. Default: 400",
        placeholder="400"
    )
    streamid: Optional[str] = Field(
        default=None,
        label="Stream ID",
        description="Optional stream identifier",
        placeholder="streamid"
    )

    video_encoder: Union[UUID, h264EncoderUnion, h265EncoderUnion] = Field(
        default_factory=lambda: x264EncoderDTO(
            options="bitrate=4000 pass=cbr speed-preset=veryfast",
            profile="main",
        ),
    )
    audio_encoder: Union[UUID, aacEncoderDTO, mp2EncoderDTO] = Field(
        default_factory=lambda: aacEncoderDTO(
            name="aac",
            options=""
        ),
    )
    mux: mpegtsMuxDTO = Field(
        default_factory=lambda: mpegtsMuxDTO(
            name = "mpegtsmux",
            options="alignment=7"
        ),
    )

from pipelines.outputs.srtserversink import SrtserversinkOutput

@router.put("/srtserversink", response_model=SuccessDTO)
async def create_srtserversink_output(request: Request, data: SrtserversinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
        safe_broadcast("UPDATE", data)
    else:
        output = SrtserversinkOutput(data=data)
        handler.add_pipeline(output)

    return data