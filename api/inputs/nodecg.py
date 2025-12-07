
from fastapi import APIRouter, Request
from pydantic import Field
from api.input_models import InputDeleteDTO, SuccessDTO
from api.inputs.wpesrc import WpesrcInputDTO

from typing import Optional, Union
from helpers import get_default_height, get_default_width

from event_loop_bridge import safe_broadcast
router = APIRouter()


class NodeCGInputDTO(WpesrcInputDTO):
    type: str =  Field(
        label="NodeCG Source",
        default="nodecg",
        description="NodeCG allows overlaying HTML and controlling its output via Dashboard panels.",
    )
    nodecg_baseurl: Optional[str] = Field(
        default=None,
        label="NodeCG base url",
        placeholder="http://localhost:9090",
        description="Only needed without proxy. Leave empty when [nodecg] config is set.",
        help="starts with http://"
    )
    panels: Union[str, list[str]] = Field(
        label="Dashboard Panels",
        placeholder="/graphics/",
        description="path(s) to NodeCG Dashboard Panel(s)",
        help="single path or list of paths"
    )
    index: Optional[int] = None
    show_controls: bool = False

from pipelines.inputs.nodecg import NodeCGInput

@router.put("/nodecg", response_model=SuccessDTO)
async def create_nodecg_input(request: Request, data: NodeCGInputDTO):
    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = NodeCGInput(data=data)
        handler.add_pipeline(input)

    return data
