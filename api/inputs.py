from typing import Annotated, Union
from uuid import UUID, uuid4
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError
from api.inputs_dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO, PlaylistInputDTO, updateInputDTO
from api.output_models import OutputDeleteDTO
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
    "update": (updateInputDTO, None),
}

unionInputDTO = Union[tuple(cls for cls, _ in INPUT_TYPE_MAPPING.values()) + (updateInputDTO,)]

async def handle_input(request: Request, data: unionInputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    print(data)
    if data.type == "update":
        print("check")
        existing_input = handler.get_pipeline("inputs", data.uid)

        if existing_input:
            print("found")
            await existing_input.update(data)

    else:
        input_class = INPUT_TYPE_MAPPING[data.type][1]
        input = input_class(data=data)
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

@router.put("/inputs", response_model=unionInputDTO)
async def create(request: Request, data: unionInputDTO = Depends(getInputDTO)):
    return await handle_input(request, data)

@router.put("/inputs/{uid}", response_model=unionInputDTO)
async def update_input(data: updateInputDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    existing_input = handler.get_pipeline("inputs", data.uid)

    if existing_input:
        updated_input = await existing_input.update(data)
        return updated_input
    else:
        raise HTTPException(status_code=404, detail="Input not found")


@router.get("/inputs")
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"] if handler._pipelines is not None else []
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())

    return descriptions

@router.delete("/inputs", response_model=SuccessDTO)
async def delete(request: Request, data: InputDeleteDTO):
    handler: "PipelineHandler" = request.app.state._state["pipeline_handler"]
    if handler.get_pipeline("inputs", data.uid) is not None:
        handler.delete_pipeline("inputs", data.uid)
        await manager.broadcast("DELETE", data)

        preview = handler.get_preview_pipeline(data.uid)
        if preview is not None:
            handler.delete_pipeline("outputs", preview.data.uid)
            await manager.broadcast("DELETE", data=(OutputDeleteDTO(uid=preview.data.uid)))

        mixers = handler.get_pipelines('mixers')
        for mixer in mixers:
            if mixer.data.type == "scene":
                while True:
                    mixerInput = mixer.data.getMixerInputDTObySource(data.uid)
                    if mixerInput is None:
                        break
                    mixer.remove_source(mixerRemoveDTO(src=data.uid, index=mixerInput.index))
    return SuccessDTO(code=200, details="OK")