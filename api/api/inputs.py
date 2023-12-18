from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException

from api.dtos import InputDTO, SuccessDTO, InputDeleteDTO
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.inputs.input import Input
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import URIInput

router = APIRouter(prefix="/inputs")


@router.get("/", response_model=list[Description])
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"]
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    print("desc", descriptions)

    return descriptions

@router.put("/", response_model=InputDTO)
async def create(request: Request, data: InputDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    match data.type:
        case("TestInput"):
            new_input = TestInput(caps=data.caps, uid=data.uid)
            handler.add_pipeline(new_input)
        case("URIInput"):
            new_input = URIInput(caps=data.caps.__dict__, uid=data.uid, uri=data.attrs["uri"])
            handler.add_pipeline(new_input)

    return data

@router.delete("/", response_model=SuccessDTO)
async def delete(request: Request, data: InputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("inputs", data.uid)
    return SuccessDTO(code=200, details="OK")

