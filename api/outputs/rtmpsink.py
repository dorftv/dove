from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional

from api.websockets import manager



router = APIRouter()


class RtmpsinkOutputDTO(OutputDTO):
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


    x264_opts: Optional[str] = Field(
        default="tune=zerolatency pass=cbr bitrate=8192",
        label="X264 Options",
        description="Options for x264enc (eg. \"tune=zerolatency pass=quant quantizer=19\")",
        placeholder="tune=zerolatency pass=cbr bitrate=8192"
    )

    h264_profile: Optional[str] = Field(
        default="baseline",
        label="X264 Profile",
        description="h264 profile to use (high-4:4:4, high-4:2:2, high-10, high, main, baseline, constrained-baseline, high-4:4:4-intra, high-4:2:2-intra, high-10-intra))",
        placeholder="baseline"
    )


from pipelines.outputs.rtmpsink import RtmpsinkOutput

@router.put("/rtmpsink", response_model=SuccessDTO)
async def create_rtmpsink_output(request: Request, data: RtmpsinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = RtmpsinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data