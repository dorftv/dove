from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional
from typing import Literal, Union
from api.encoder import x264EncoderDTO, aacEncoderDTO, mp2EncoderDTO, muxDTO, mpegtsMuxDTO, vah264encEncoderDTO

from api.websockets import manager



router = APIRouter()

# @TODO improve codec handling
class SrtserversinkOutputDTO(OutputDTO):
    type: str = Field(
        label="SRT Sink",
        default="srtserversink",
        description="stream output to SRT Server.",
    )
    uri: str = Field(
        label="Uri",
        description="Enter SRT Server URL and Port",
        placeholder="srt://server:port"
    )
    latency: int = Field(
        label="latency",
        default=400,
        description="",
        placeholder="default: 400"
    )
    streamid: Optional[str] = Field(
        default=None,
        label="Stream ID",
        description="Optional stream identifier",
        placeholder="streamid"
    )

    video_encoder: Union[x264EncoderDTO, vah264encEncoderDTO] = Field(
        default_factory=lambda: x264EncoderDTO(
            options="bitrate=4000 pass=cbr speed-preset=veryfast",
            profile="main",
        )
    )
    audio_encoder: Union[aacEncoderDTO] = Field(
        default_factory=lambda: aacEncoderDTO(
            name="aac",
            options=""
        )
    )
    mux: mpegtsMuxDTO = Field(
        default_factory=lambda: mpegtsMuxDTO(
            name = "mpegts",
            options="alignment=7"
        )
    )


from pipelines.outputs.srtserversink import SrtserversinkOutput

@router.put("/srtserversink", response_model=SuccessDTO)
async def create_srtsink_output(request: Request, data: SrtserversinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = SrtserversinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data