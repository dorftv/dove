# main.py
from fastapi import Request, APIRouter, HTTPException
from pydantic import ValidationError
from api.mixers_dtos import mixerDTO, mixerCutDTO, mixerInputDTO, mixerInputsDTO
from pipelines.base import GSTBase
import json

router = APIRouter(prefix="/api")


# @ TODO check if mixer and input exist
@router.post("/cut")
async def action_cut(request: Request, item: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", item.target)

    mixer.cut(item)
    return item

@router.post("/overlay")
async def action_overlay(request: Request, item: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", item.target)

    mixer.overlay(item)
    return item

@router.post("/remove")
async def action_remove(request: Request, item: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", item.target)

    mixer.remove(item)
    return item    
