from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Literal, Union, Optional
from api.encoder.video_encoder import h264EncoderUnion, x264EncoderDTO
from api.encoder.audio_encoder import aacEncoderDTO, mp2EncoderDTO, opusEncoderDTO
from api.websockets import manager



router = APIRouter()


class whipclientsinkOutputDTO(OutputDTO):
    type: str = Field(
        label="Whip Client Sink",
        default="whipclientsink",
        description="stream output to a WHIP server.",
    )
    video_encoder: h264EncoderUnion = Field(
        default_factory=lambda: x264EncoderDTO(),


    #audio_encoder: Union[opusEncoderDTO] = Field(
    #    default_factory=lambda: aacEncoderDTO(
    #        name="opus",
    #        options=""
    #    )
    )

from pipelines.outputs.whipclientsink import whipclientsinkOutput

@router.put("/hlssink2", response_model=SuccessDTO)
async def create_rtmpsink_output(request: Request, data: whipclientsinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = whipclientOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data