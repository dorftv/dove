from typing import Annotated
from uuid import UUID, uuid4
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError
from api.inputs_dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO, PlaylistInputDTO
from caps import Caps
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import UriInput
from pipelines.inputs.wpe_input import WpeInput
from pipelines.inputs.ytdlp_input import ytDlpInput
from pipelines.inputs.playlist_input import PlaylistInput

from api.outputs_dtos import OutputDTO, OutputDeleteDTO
from api.mixers_dtos import mixerDTO, mixerRemoveDTO
from api.websockets import manager

# @TODO find a better place
from pipelines.outputs.preview_hls_output import previewHlsOutput
from api.outputs_dtos import previewHlsOutputDTO
from pipeline_handler import HandlerSingleton


router = APIRouter(prefix="/api")

unionInputDTO = Union[TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO, PlaylistInputDTO]

async def handle_input(request: Request, data: unionInputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    # Handle based on the type of data
    if isinstance(data, TestInputDTO):
        input = TestInput(data=data)
    elif isinstance(data, UriInputDTO):
        input = UriInput(data=data)
    elif isinstance(data, WpeInputDTO):
        input = WpeInput(data=data)    
    elif isinstance(data, ytDlpInputDTO):
        input = ytDlpInput(data=data)
    elif isinstance(data, PlaylistInputDTO):
        input = PlaylistInput(data=data)                   
    else:
        raise HTTPException(status_code=400, detail="Invalid input type")

    existing_input = handler.get_pipeline("inputs", data.uid)

    if existing_input:
        existing_input.data = data
    else:
        handler.add_pipeline(input)

    await manager.broadcast("CREATE", data)

    return data



async def getInputDTO(request: Request) -> unionInputDTO:
    json_data = await request.json()
    input_type = json_data.get("type")
    try:
        if input_type == "testsrc":
            return TestInputDTO(**json_data)
        elif input_type == "urisrc":
            return UriInputDTO(**json_data)
        elif input_type == "wpesrc":
            return WpeInputDTO(**json_data)
        elif input_type == "ytdlpsrc":
            return ytDlpInputDTO(**json_data)     
        elif input_type == "playlist":
            return PlaylistInputDTO(**json_data)                             
        else:
            raise HTTPException(status_code=400, detail=f"Invalid input type: {input_type}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

@router.get("/inputs")
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"]
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    return descriptions

# @TODO handle updates
@router.put("/inputs")
async def create(request: Request, data: unionInputDTO = Depends(getInputDTO)):
    return await handle_input(request, data)


@router.delete("/inputs", response_model=SuccessDTO)
async def delete(request: Request, data: InputDeleteDTO):
    handler: "PipelineHandler" = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("inputs", data.uid)
    # cleanup related stuff
    preview = handler.get_preview_pipeline(data.uid)
    handler.delete_pipeline("outputs", preview.data.uid)
    mixers = handler.get_pipelines('mixers')
    for mixer in mixers:
       mixer.remove(mixerRemoveDTO(src=data.uid))

    await manager.broadcast("DELETE", data)
    await manager.broadcast("DELETE", data=(OutputDeleteDTO(uid=preview.data.uid )))

    return SuccessDTO(code=200, details="OK")

