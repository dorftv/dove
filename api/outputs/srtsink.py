from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional

from api.websockets import manager



router = APIRouter()


class SrtsinkOutputDTO(OutputDTO):
    type: str = "srtsink"

    uri: str = Field(
        label="Uri",
        description="Enter SRT Server URL and Port",
        placeholder="srt://server:port"
    )

    streamid: Optional[str] = Field(
        default=None,
        label="Stream ID",
        description="Optional stream identifier",
        placeholder="streamid"
    )


from pipelines.outputs.srtsink import SrtsinkOutput

@router.put("/srtsink", response_model=SuccessDTO)
async def create_srtsink_output(request: Request, data: SrtsinkOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = SrtsinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data