
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from api.websockets import manager
router = APIRouter()


class TestsrcInputDTO(InputDTO):
    type: str =  Field(
        label="Test Source",
        default="testsrc",
        description="Adds videotestsrc and audiotestsrc.",
    )
    pattern: Optional[int] =  Field(
        label="Pattern",
        default=1,
        description="Pattern to draw",
        help="Allowed values: 1-25",
        placeholder="1",
    )
    wave: Optional[int] = Field(
        label="Pattern",
        default=1,
        description="Waveform for Audio",
        help="Allowed values 1-12",
        placeholder="1",
    )
    freq: Optional[float] = Field(
        label="Frequency",
        default=440.0,
        description="Frequency for Audio.",
        placeholder="440.0",
    )
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)

from pipelines.inputs.testsrc import TestsrcInput

@router.put("/testsrc", response_model=SuccessDTO)
async def create_testsrc_input(request: Request, data: TestsrcInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
    else:
        input = TestsrcInput(data=data)
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data