from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional

from api.websockets import manager



router = APIRouter()

class Shout2sendOutputDTO(OutputDTO):
    type: str = "shout2send"
    mount: str
    ip: str
    port: int
    username: str
    password: str


from pipelines.outputs.shout2send import Shout2sendOutput

@router.put("/shout2send", response_model=SuccessDTO)
async def create_srtsink_output(request: Request, data: Shout2sendOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = DecklinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data