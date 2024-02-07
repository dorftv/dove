from typing import Annotated
from uuid import UUID, uuid4
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError
from api.inputs_dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO, PlaylistInputDTO
from api.outputs_dtos import OutputDeleteDTO
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import UriInput
from pipelines.inputs.wpe_input import WpeInput
from pipelines.inputs.ytdlp_input import ytDlpInput
from pipelines.inputs.playlist_input import PlaylistInput

from api.mixers_dtos import mixerDTO, mixerRemoveDTO
from api.websockets import manager

from pipeline_handler import HandlerSingleton


router = APIRouter(prefix="/api")

INPUT_TYPE_MAPPING = {
    "testsrc": (TestInputDTO, TestInput),
    "urisrc": (UriInputDTO, UriInput),
    "wpesrc": (WpeInputDTO, WpeInput),
    "ytdlpsrc": (ytDlpInputDTO, ytDlpInput),
    "playlist": (PlaylistInputDTO, PlaylistInput),
}

unionInputDTO = Union[tuple(cls for cls, _ in INPUT_TYPE_MAPPING.values())]

# @TODO handle updates
async def handle_input(request: Request, data: unionInputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    input_class = INPUT_TYPE_MAPPING[data.type][1]
    input = input_class(data=data)

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
        dto_class = INPUT_TYPE_MAPPING[input_type][0]
        return dto_class(**json_data)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid input type: {input_type}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


@router.put("/inputs")
async def create(request: Request, data: unionInputDTO = Depends(getInputDTO)):
    return await handle_input(request, data)


@router.get("/inputs")
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"]
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    return descriptions


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

