from typing import Annotated
from uuid import UUID
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError
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


async def handle_input(request: Request, data: Union[TestInputDTO, UriInputDTO]):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    caps = Caps(video="video/x-raw,width=1280,height=720,framerate=25/1",
                audio="audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)48000, channels=(int)2")

    # Handle based on the type of data
    if isinstance(data, TestInputDTO):
        input = TestInput(caps=caps, uid=data.uid, pattern=data.pattern)
    elif isinstance(data, UriInputDTO):
        input = URIInput(caps=caps, uid=data.uid, uri=data.uri)
    else:
        raise HTTPException(status_code=400, detail="Invalid input type")

    handler.add_pipeline(input)
    await ws_broadcast(data)
    return data


async def getInputDTO(request: Request) -> Union[UriInputDTO, TestInputDTO]:
    json_data = await request.json()
    input_type = json_data.get("type")
    try:
        if input_type == "test":
            return TestInputDTO(**json_data)
        elif input_type == "uri":
            return UriInputDTO(**json_data)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid input type: {input_type}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

# @TODO Fix getting List
@router.get("/inputs", response_model=list[InputDTO])
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"]
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    return descriptions

# @TODO handle updates
@router.put("/inputs")
async def create(request: Request, data: Union[TestInputDTO, UriInputDTO] = Depends(getInputDTO)):
    return await handle_input(request, data)


@router.delete("/inputs", response_model=SuccessDTO)
async def delete(request: Request, data: InputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("inputs", data.uid)
    return SuccessDTO(code=200, details="OK")

