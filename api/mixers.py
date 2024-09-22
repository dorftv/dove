from typing import Annotated
from uuid import UUID
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError

from api.mixers_dtos import mixerDTO, SuccessDTO, MixerDeleteDTO, sceneMixerDTO,  programMixerDTO
from api.websockets import manager
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.mixers.scene_mixer import sceneMixer


# @TODO find a better place
from api.outputs.hlssink2 import hlssink2OutputDTO
from pipelines.outputs.hlssink2 import hlssink2Output
from api.output_models import OutputDTO, OutputDeleteDTO

from uuid import UUID, uuid4

router = APIRouter(prefix="/api")

MIXER_TYPE_MAPPING = {
    "scene": (sceneMixerDTO, sceneMixer),
}


unionMixerDTO = Union[sceneMixerDTO]

async def handle_mixer(request: Request, data: unionMixerDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer_class = MIXER_TYPE_MAPPING[data.type][1]
    mixer = mixer_class(data=data)

    existing_mixer = handler.get_pipeline("mixers", data.uid)

    if existing_mixer:
        existing_mixer.data = data
    else:
        handler.add_pipeline(mixer)
        output = PreviewHlsOutput(data=hlssink2OutputDTO(src=data.uid))
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data



async def getMixerDTO(request: Request) -> unionMixerDTO:
    json_data = await request.json()
    mixer_type = json_data.get("type")
    try:
        dto_class = MIXER_TYPE_MAPPING[mixer_type][0]
        return dto_class(**json_data)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid mixer type: {mixer_type}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


@router.get("/mixers")
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixers: list[Mixer] = handler._pipelines["mixers"] if handler._pipelines is not None else []
    descriptions: list[Description] = []

    for pipeline in mixers:
        descriptions.append(pipeline.describe())

    return descriptions


@router.put("/mixers")
async def create(request: Request, data: unionMixerDTO = Depends(getMixerDTO)):
    return await handle_mixer(request, data)


@router.delete("/mixers", response_model=SuccessDTO)
async def delete(request: Request, data: MixerDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("mixers", data.uid)
    preview = handler.get_preview_pipeline(data.uid)
    handler.delete_pipeline("outputs", preview.data.uid)

    await manager.broadcast("DELETE", data)
    await manager.broadcast("DELETE", data=(OutputDeleteDTO(uid=preview.data.uid )))
    # @TODO handle output deletion
    return SuccessDTO(code=200, details="OK")

