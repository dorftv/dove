# main.py
from fastapi import Request, APIRouter, HTTPException
from pydantic import ValidationError
from api.mixers_dtos import mixerDTO, mixerCutDTO, mixerInputDTO, mixerInputsDTO, mixerPadDTO
from pipelines.base import GSTBase
import json

router = APIRouter(prefix="/api")


# @ TODO check if mixer and input exist
@router.post("/mixer/add_source")
async def action_add_source(request: Request, data: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.target)

    response = mixer.add_source(data)
    return response

@router.post("/mixer/remove_source")
async def action_remove_source(request: Request, data: mixerCutDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.target)

    response = mixer.remove_source(data)
    return response

@router.post("/mixer/add_pad")
async def action_add_pad(request: Request, data: mixerPadDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.uid)

    response = mixer.add_pads()
    return response

@router.post("/mixer/remove_pad")
async def action_remove_pad(request: Request, data: mixerPadDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.uid)

    response = mixer.remove_pads(data.sink)
    return response