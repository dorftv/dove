from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from event_loop_bridge import safe_broadcast
router = APIRouter()


class V4l2srcInputDTO(InputDTO):
    type: str = Field(
        label="Webcam",
        default="v4l2src",
        description="Capture video from a V4L2 device (webcam).",
    )
    device: Optional[str] = Field(
        label="Video Device",
        default="/dev/video0",
        description="Video device path.",
        placeholder="/dev/video0",
    )
    audio_device: Optional[str] = Field(
        label="Audio Device",
        default="",
        description="ALSA audio device (e.g. hw:1,0). Leave empty for silence.",
        placeholder="hw:1,0",
    )
    show_controls: bool = False

    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)

from pipelines.inputs.v4l2src import V4l2srcInput

@router.put("/v4l2src", response_model=SuccessDTO)
async def create_v4l2src_input(request: Request, data: V4l2srcInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = V4l2srcInput(data=data)
        handler.add_pipeline(input)

    return data
