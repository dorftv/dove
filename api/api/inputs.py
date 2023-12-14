from typing import Annotated

from fastapi import APIRouter, Request, HTTPException

from models.input import InputDTO, InputCreateDTO, InputTypes
from models import input
from pipelines.hls_monitor import HLSMonitorPipeline
from pipelines.inputs import TestPipeline

router = APIRouter(prefix="/inputs")


@router.get("/", response_model=list[input.InputCreateDTO])
async def all(request: Request):
    handler = request.app.state._state["pipeline_handler"]
    inputs = handler.pipelines["inputs"]
    descriptions: list[input.Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    return descriptions


@router.delete("/")
async def delete(request: Request, input: InputDTO):
    handler = request.app.state._state["pipeline_handler"]
    inputs = handler.pipelines["inputs"]

    for pipeline in inputs:
        if pipeline.uid == input.uid:
            handler.add_pipeline(HLSMonitorPipeline())
            pipeline.stop()
            inputs.remove(pipeline)

    return "OK"


@router.put("/")
async def create_or_update(input: InputCreateDTO, request: Request):
    handler = request.app.state._state["pipeline_handler"]
    mapping = {
        InputTypes.test_src: TestPipeline
    }

    try:
        pipeline = mapping[input.type](
            type=input.type,
            name=input.name,
            state=input.state,
            height=input.height,
            width=input.width,
            preview=input.preview
        )
        handler.add_pipeline(pipeline)
        pipeline.set_state(input.state)

        preview_pipeline = HLSMonitorPipeline(f"video_{pipeline.uid}", pipeline.uid.hex, input.width, input.height)
        handler.add_pipeline(preview_pipeline)
        preview_pipeline.play()
    except KeyError:
        HTTPException(400, detail=f"cannot find pipeline of type {input.type}")

