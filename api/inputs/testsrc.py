
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDTO, InputDeleteDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from api.websockets import manager
router = APIRouter()


class TestsrcInputDTO(InputDTO):
    type: str = "testsrc"
    pattern: Optional[int] = 1
    wave: Optional[int] = 1
    freq: Optional[float] = 440.0
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