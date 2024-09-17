
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDeleteDTO, SuccessDTO
from api.inputs.wpesrc import WpesrcInputDTO
#### <pt
from typing import Optional
from helpers import get_default_height, get_default_width

from api.websockets import manager
router = APIRouter()


class NodeCGInputDTO(WpesrcInputDTO):
    type: str =  Field(
        label="ModeCG Source",
        default="nodecg",
        description="NodeCG allows overlaying HTML and controlling its output via Dashboard panels.",
    )
    nodecg_baseurl: str =  Field(
        label="NodeCG base url",
        placeholder="http://localhost:9090",
        description="Enter the NodeCG base url.",
        help="starts with http://"
    )
    panels: str =  Field(
        label="Dashboard Panels",
        placeholder="/graphics/",
        description="path to NodeCG Dashboard Panel",
        help=""
    )
    index: Optional[int] = None

from pipelines.inputs.nodecg import NodeCGInput

@router.put("/nodecg", response_model=SuccessDTO)
async def create_nodecg_input(request: Request, data: NodeCGInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
    else:
        input = NodeCGInput(data=data)
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data