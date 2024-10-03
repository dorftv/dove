# main.py
from fastapi import Request, APIRouter, HTTPException
from pydantic import ValidationError
from api.mixers_dtos import mixerDTO, mixerCutDTO, mixerInputDTO, mixerInputsDTO, mixerSlotDTO, mixerCutProgramDTO, mixerRemoveSlotDTO
from pipelines.base import GSTBase
import json

router = APIRouter(prefix="/api")



@router.post("/mixer/cut_program")
async def action_cut_program(request: Request, data: mixerCutProgramDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    program: mixerMixerDTO = handler.get_program()
    print(program)
    response = await program.cut_program(data)
    return response


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

@router.post("/mixer/add_slot")
async def action_add_slot(request: Request, data: mixerSlotDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.uid)
    response = mixer.add_slot(data.slot)
    return response

@router.post("/mixer/remove_slot")
async def action_remove_slot(request: Request, data: mixerRemoveSlotDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixer: mixerMixerDTO = handler.get_pipeline("mixers", data.uid)
    inputDTO: mixerInputDTO = mixer.data.getMixerInputDTO(data.index)
    response = mixer.remove_slot(inputDTO)
    return response