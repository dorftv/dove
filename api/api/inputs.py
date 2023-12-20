from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import create_model

from api.dtos import InputDTO, SuccessDTO, InputDeleteDTO
from caps import Caps
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.inputs.input import Input
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import URIInput
from websocket_handler import  ws_broadcast

router = APIRouter(prefix="/api")


@router.get("/inputs", response_model=list[InputDTO])
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"]
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    return descriptions

@router.put("/inputs", response_model=InputDTO)
async def create(request: Request, data: InputDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    match data.type:
        case("TestInput"):
            caps = Caps(video="video/x-raw,width=1280,height=720,framerate=25/1", audio="audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2")
            attrs_model = create_model("Attrs", **{key: (value[0], ... if value[1] else None) for key, value in TestInput.schema.items()})

            new_input = TestInput(caps=caps, uid=data.uid, name=data.name, state=data.state, attrs=attrs_model(**data.attrs))
            handler.add_pipeline(new_input)
            # emit websocket
            # TODO send data like we need them in frontend
            await ws_broadcast(data)            
        case("URIInput"):
            caps = Caps(video="video/x-raw,width=1280,height=720,framerate=25/1", audio="audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2")
            new_input = URIInput(caps=caps, uid=data.uid, name=data.name, state=data.state, attrs=URIInput.get_attr_type()(**data.attrs))
            handler.add_pipeline(new_input)

    return data

@router.delete("/inputs", response_model=SuccessDTO)
async def delete(request: Request, data: InputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("inputs", data.uid)
    return SuccessDTO(code=200, details="OK")

