from fastapi import APIRouter, Request
from pydantic import Field
from dove.api.output_models import OutputDTO, SuccessDTO
from typing import Optional, Union
from uuid import UUID
from dove.api.encoder.video_encoder import h264EncoderUnion, x264EncoderDTO
from dove.api.encoder.audio_encoder import aacEncoderDTO
from dove.event_loop_bridge import safe_broadcast
from dove.api.helper import create_or_raise



router = APIRouter()


class hlssink2OutputDTO(OutputDTO):
    type: str = Field(
        label="HLS Sink",
        default="hlssink2",
        description="stream output to HLS.",
    )
    # Previews pass encoder UUIDs; user-created outputs get these defaults
    video_encoder: Union[UUID, h264EncoderUnion] = Field(
        default_factory=lambda: x264EncoderDTO(
            options="bitrate=4000 pass=cbr speed-preset=veryfast key-int-max=60",
        ),
    )
    audio_encoder: Optional[Union[UUID, aacEncoderDTO]] = Field(
        default_factory=lambda: aacEncoderDTO(name="aac", options=""),
    )

@router.put("/hlssink2", response_model=SuccessDTO)
async def create_hlssink2_output(request: Request, data: hlssink2OutputDTO):
    from dove.pipelines.outputs.hlssink2 import hlssink2Output
    handler = request.app.state.pipeline_handler
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
        safe_broadcast("UPDATE", data)
    else:
        output = hlssink2Output(data=data)
        await create_or_raise(handler, output)

    return data