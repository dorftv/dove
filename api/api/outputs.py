from typing import Annotated
from uuid import UUID
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError
from api.outputs_dtos import OutputDTO, SuccessDTO, OutputDeleteDTO, previewHlsOutputDTO, srtOutputDTO
from api.websockets import manager
from caps import Caps
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.outputs.preview_hls_output import previewHlsOutput
from pipelines.outputs.srt_output import srtOutput

router = APIRouter(prefix="/api")

unionOutputDTO =  Union[previewHlsOutputDTO, srtOutputDTO]


async def handle_output(request: Request, data: unionOutputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]

    # Handle based on the type of data
    if isinstance(data, previewHlsOutputDTO):
        output = previewHlsOutput(data=data)
    elif isinstance(data, srtOutputDTO):
        output = srtOutput(data=data)
    else:
        raise HTTPException(status_code=400, detail="Invalid output type")

    handler.add_pipeline(output)
    await manager.broadcast("CREATE", data)
    return data


async def getOutputDTO(request: Request) -> unionOutputDTO:
    json_data = await request.json()
    output_type = json_data.get("type")
    try:
        if output_type == "preview_hls":
            return previewHlsOutputDTO(**json_data)
        elif output_type == "srtsink":
            return srtOutputDTO(**json_data)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid output type: {output_type}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

@router.get("/outputs")
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    outputs: list[Output] = handler._pipelines["outputs"]
    descriptions: list[Description] = []

    for pipeline in outputs:
        descriptions.append(pipeline.describe())

    return descriptions

# @TODO handle updates
@router.put("/outputs")
async def create(request: Request, data: unionOutputDTO = Depends(getOutputDTO)):
    return await handle_output(request, data)


@router.delete("/outputs", response_model=SuccessDTO)
async def delete(request: Request, data: OutputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("outputs", data.uid)
    await manager.broadcast("DELETE", data)
      
    return SuccessDTO(code=200, details="OK")

