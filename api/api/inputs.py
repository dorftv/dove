from typing import Annotated
from uuid import UUID
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends

from api.dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO
from caps import Caps
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.inputs.input import Input
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import URIInput
from websocket_handler import  ws_broadcast

router = APIRouter(prefix="/api")

async def handle_test_input(request, data: TestInputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    #we don't need caps for input
    caps = Caps(video="video/x-raw,width=1280,height=720,framerate=25/1", audio="audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2")

    # needs fixing
    #new_input = TestInput(caps=caps, uid=data.uid, uri=data.uri)
    #handler.add_pipeline(new_input)
    # emit websocket
    # TODO send data like we need them in frontend
    await ws_broadcast(data)     
    # Logic for handling Test input
    return {"message": "Test input created"}

async def handle_uri_input(request, data: UriInputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    #we don't need caps for input
    #caps = Caps(video="video/x-raw,width=1280,height=720,framerate=25/1", audio="audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2")
    
    # needs fixing    
    #new_input = URIInput(caps=caps, uid=data.uid, uri=data.uri)
    #handler.add_pipeline(new_input)    
    return {"message": "URI input created"}


@router.get("/inputs", response_model=list[InputDTO])
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"]
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    return descriptions


@router.put("/inputs")
async def create(request: Request, data: Union[TestInputDTO, UriInputDTO]):
    if data.type == "test":
        if not isinstance(data, TestInputDTO):
            raise HTTPException(status_code=400, detail="Invalid input for type 'test'")
        return await handle_test_input(request, data)
    elif data.type == "uri":
        if not isinstance(data, UriInputDTO):
            raise await HTTPException(status_code=400, detail="Invalid input for type 'uri'")
        return await handle_uri_input(request, data)
    else:
        raise HTTPException(status_code=400, detail="Invalid input type")



@router.delete("/inputs", response_model=SuccessDTO)
async def delete(request: Request, data: InputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("inputs", data.uid)
    return SuccessDTO(code=200, details="OK")

