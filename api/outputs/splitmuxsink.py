from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Literal, Optional, Union
from uuid import UUID
from api.encoder.video_encoder import h264EncoderUnion, h265EncoderUnion, x264EncoderDTO, vp8EncoderDTO, vp9EncoderDTO, av1EncoderDTO
from api.encoder.audio_encoder import aacEncoderDTO, mp2EncoderDTO, vorbisEncoderDTO, flacEncoderDTO, opusEncoderDTO
from api.encoder.mux import mp4MuxDTO, matroskaMuxDTO, mpegtsMuxDTO

from event_loop_bridge import safe_broadcast
from api.helper import create_or_raise


router = APIRouter()

class splitmuxsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="SplitMux Sink",
        default="splitmuxsink",
        description="Record to segmented files.",
    )
    location: Optional[str] = Field(
        default="/var/dove/recordings/%Y-%m-%d/recording_%H-%M-%S",
        label="Location",
        description="File path pattern (strftime format, extension auto-added from mux)",
        placeholder="/var/dove/recordings/%Y-%m-%d/recording_%H-%M-%S",
    )
    segment_duration: Literal["30m", "1h", "2h", "4h", "6h"] = Field(
        default="1h",
        label="Segment Duration",
        description="Duration of each recording segment (first segment aligns to clock boundary)",
    )
    video_encoder: Union[UUID, h264EncoderUnion, h265EncoderUnion, vp8EncoderDTO, vp9EncoderDTO, av1EncoderDTO] = Field(
        default_factory=lambda: x264EncoderDTO(
            options="bitrate=4000 pass=cbr speed-preset=veryfast",
            profile="main",
        ),
    )
    audio_encoder: Union[UUID, aacEncoderDTO, mp2EncoderDTO, vorbisEncoderDTO, flacEncoderDTO, opusEncoderDTO] = Field(
        default_factory=lambda: aacEncoderDTO(
            name="aac",
            options=""
        ),
    )
    mux: Union[mp4MuxDTO, matroskaMuxDTO, mpegtsMuxDTO] = Field(
        default_factory=lambda: mp4MuxDTO(
            name="mp4mux",
            options="fragment-duration=1000 latency=4000000000"
        ),
    )

from pipelines.outputs.splitmuxsink import splitmuxsinkOutput

@router.put("/splitmuxsink", response_model=SuccessDTO)
async def create_splitmuxsink_output(request: Request, data: splitmuxsinkOutputDTO):
    handler = request.app.state.pipeline_handler
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
        safe_broadcast("UPDATE", data)
    else:
        output = splitmuxsinkOutput(data=data)
        await create_or_raise(handler, output)

    return data
