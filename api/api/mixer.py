# main.py
from fastapi import Request, APIRouter, HTTPException
from pydantic import ValidationError
from api.mixers_dtos import mixerDTO, mixerCutDTO, mixerInputDTO, mixerInputsDTO
from pipelines.base import GSTBase
import json

router = APIRouter(prefix="/api")


# @ TODO check if mixer and input exist
@router.post("/cut")
async def action_cut(request: Request, data: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.target)

    mixer.cut(data)
    return data

@router.post("/overlay")
async def action_overlay(request: Request, data: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.target)

    mixer.overlay(mixerInputDTO(src=data.src))
    return data

@router.post("/remove")
async def action_remove(request: Request, data: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.target)

    mixer.remove(data)
    return data    
