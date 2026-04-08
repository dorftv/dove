from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError

from api.mixers_dtos import SuccessDTO, MixerDeleteDTO, sceneMixerDTO
from api.auth import require_role, require_read
from event_loop_bridge import safe_broadcast
from api.helper import create_or_raise
from pipeline_handler import PipelineHandler

from pipelines.base import GSTBase
from pipelines.mixers.scene_mixer import sceneMixer

router = APIRouter(prefix="/api")

MIXER_TYPE_MAPPING = {
    "scene": (sceneMixerDTO, sceneMixer),
}


unionMixerDTO = Union[sceneMixerDTO]

async def handle_mixer(request: Request, data: unionMixerDTO):
    handler: GSTBase = request.app.state.pipeline_handler
    mixer_class = MIXER_TYPE_MAPPING[data.type][1]
    mixer = mixer_class(data=data)

    existing_mixer = handler.get_pipeline("mixers", data.uid)
    if existing_mixer:
        existing_mixer.data = data
        safe_broadcast("UPDATE", data)
    else:
        await create_or_raise(handler, mixer)

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


@router.get("/mixers", dependencies=[require_read()])
async def all(request: Request):
    handler: GSTBase = request.app.state.pipeline_handler
    mixers: list[Mixer] = handler._pipelines["mixers"] if handler._pipelines is not None else []
    descriptions = []

    for pipeline in mixers:
        descriptions.append(pipeline.describe())

    return descriptions


@router.put("/mixers", dependencies=[require_role("supervisor")])
async def create(request: Request, data: unionMixerDTO = Depends(getMixerDTO)):
    return await handle_mixer(request, data)


@router.delete("/mixers", response_model=SuccessDTO, dependencies=[require_role("supervisor")])
async def delete(request: Request, data: MixerDeleteDTO):
    handler: PipelineHandler = request.app.state.pipeline_handler
    pipeline = handler.get_pipeline("mixers", data.uid)
    if pipeline is not None and getattr(pipeline.data, 'locked', False):
        raise HTTPException(status_code=403, detail="Mixer is locked")
    # delete_pipeline handles preview cleanup + DELETE broadcasts
    handler.delete_pipeline("mixers", data.uid)
    return SuccessDTO(code=200, details="OK")

