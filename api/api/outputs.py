from typing import Annotated
from uuid import UUID
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError
from api.outputs_dtos import OutputDTO, SuccessDTO, OutputDeleteDTO, previewHlsOutputDTO, srtOutputDTO, decklinkOutputDTO
from api.websockets import manager
from caps import Caps
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.outputs.preview_hls_output import previewHlsOutput
from pipelines.outputs.srt_output import srtOutput
from pipelines.outputs.decklink_output import decklinkOutput


router = APIRouter(prefix="/api")



OUTPUT_TYPE_MAPPING = {
    "preview_hls": (previewHlsOutputDTO, previewHlsOutput),
    "srtsink": (srtOutputDTO, srtOutput),
    "decklinksink": (decklinkOutputDTO, decklinkOutput),
}

unionOutputDTO = Union[tuple(cls for cls, _ in OUTPUT_TYPE_MAPPING.values())]

# @TODO handle updates
async def handle_output(request: Request, data: unionOutputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    output_class = OUTPUT_TYPE_MAPPING[data.type][1]
    output = output_class(data=data)

    existing_output = handler.get_pipeline("outputs", data.uid)

    if existing_output:
        existing_output.data = data
    else:
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data


async def getOutputDTO(request: Request) -> unionOutputDTO:
    json_data = await request.json()
    output_type = json_data.get("type")
    try:
        dto_class = OUTPUT_TYPE_MAPPING[output_type][0]
        return dto_class(**json_data)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid output type: {output_type}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

# @TODO handle updates
@router.put("/outputs")
async def create(request: Request, data: unionOutputDTO = Depends(getOutputDTO)):
    return await handle_output(request, data)


@router.get("/outputs")
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    outputs: list[Output] = handler._pipelines["outputs"]
    descriptions: list[Description] = []

    for pipeline in outputs:
        descriptions.append(pipeline.describe())

    return descriptions


@router.delete("/outputs", response_model=SuccessDTO)
async def delete(request: Request, data: OutputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("outputs", data.uid)
    await manager.broadcast("DELETE", data)
      
    return SuccessDTO(code=200, details="OK")

