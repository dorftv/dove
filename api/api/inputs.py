from typing import Annotated

from fastapi import APIRouter, Request, HTTPException

from models.input import InputDTO, InputCreateDTO, InputTypes
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.inputs.input import Input

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

