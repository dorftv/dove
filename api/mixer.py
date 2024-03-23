# main.py
from fastapi import Request, APIRouter, HTTPException
from pydantic import ValidationError
from api.mixers_dtos import mixerDTO, mixerCutDTO, mixerInputDTO, mixerInputsDTO, mixerPadDTO, mixerCutProgramDTO
from pipelines.base import GSTBase
import json

router = APIRouter(prefix="/api")



@router.post("/mixer/cut_program")
async def action_cur_program(request: Request, data: mixerCutProgramDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    program: mixerMixerDTO = handler.get_program()
    print(program)
    response = program.cut_program(data)
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