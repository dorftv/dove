
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDeleteDTO, SuccessDTO
from api.inputs.wpesrc import WpesrcInputDTO
from typing import Optional
from helpers import get_default_height, get_default_width

from api.websockets import manager
router = APIRouter()


class NodecgInputDTO(WpesrcInputDTO):
    type: str =  Field(
        label="NodeCG Source",
        default="nodecg",
        description="Nodecg uses Wpesrc for Html overlay.",
    )
    nodecg_baseurl: Optional[str] =  Field(
        label="NodeCG base url",
        default="",
        placeholder="http://localhost:9090",
        description="Enter the NodeCG base url.",
        help="starts with http://"
    )
    panels: Optional[str] =  Field(
        label="Dashboard Panels",
        default="",
        placeholder="/graphics/",
        description="path to NodeCG Dashboard Panel",
        help=""
    )
    index: Optional[int] = None

from pipelines.inputs.wpesrc import WpesrcInput

@router.put("/nodecg", response_model=SuccessDTO)
async def create_wpesrc_input(request: Request, data: NodecgInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
    else:
        input = WpesrcInput(data=data)
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data