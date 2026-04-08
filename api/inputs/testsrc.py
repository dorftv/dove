
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from event_loop_bridge import safe_broadcast
from api.helper import create_or_raise
router = APIRouter()


class TestsrcInputDTO(InputDTO):
    type: str =  Field(
        label="Test Source",
        default="testsrc",
        description="Adds videotestsrc and audiotestsrc.",
    )
    pattern: Optional[int] =  Field(
        label="Pattern",
        default=0,
        description="Pattern to draw (0=SMPTE, 1=snow, 2=black, 18=ball, etc.)",
        help="Allowed values: 0-25",
        placeholder="0",
    )
    wave: Optional[int] = Field(
        label="Waveform",
        default=8,
        description="Waveform for Audio (0=sine, 4=silence, 8=ticks, etc.)",
        help="Allowed values 0-12",
        placeholder="8",
    )
    freq: Optional[float] = Field(
        label="Frequency",
        default=440.0,
        description="Frequency for Audio.",
        placeholder="440.0",
    )
    show_controls: bool = False

    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)

from pipelines.inputs.testsrc import TestsrcInput

@router.put("/testsrc", response_model=SuccessDTO)
async def create_testsrc_input(request: Request, data: TestsrcInputDTO):
    handler = request.app.state.pipeline_handler
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = TestsrcInput(data=data)
        await create_or_raise(handler, input)

    return data