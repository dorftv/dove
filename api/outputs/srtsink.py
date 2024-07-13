from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional

from api.websockets import manager



router = APIRouter()


class SrtsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="SRT Sink",
        default="srtsink",
        description="stream output to SRT Server.",
    )
    uri: str = Field(
        label="Uri",
        description="Enter SRT Server URL and Port",
        placeholder="srt://server:port"
    )

    streamid: Optional[str] = Field(
        default=None,
        label="Stream ID",
        description="Optional stream identifier",
        placeholder="streamid"
    )

    x264_opts: Optional[str] = Field(
        default="key-int-max=30 tune=zerolatency speed-preset=slower",
        label="X264 Options",
        description="Options for x264enc (eg. \"tune=zerolatency pass=quant quantizer=19\")",
        placeholder="tune=zerolatency pass=cbr bitrate=8192"
    )

    h264_profile: Optional[str] = Field(
        default="high",
        label="X264 Profile",
        description="h264 profile to use (high-4:4:4, high-4:2:2, high-10, high, main, baseline, constrained-baseline, high-4:4:4-intra, high-4:2:2-intra, high-10-intra))",
        placeholder="high"
    )

    audio_codec: Optional[str] = Field(
        default="aac",
        label="Audio Codec",
        description="audio codec to use (aac, mp2, mp3)",
        placeholder="aac"
    )


from pipelines.outputs.srtsink import SrtsinkOutput

@router.put("/srtsink", response_model=SuccessDTO)
async def create_srtsink_output(request: Request, data: SrtsinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = SrtsinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data