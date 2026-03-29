from fastapi import Request, APIRouter, HTTPException
from pydantic import BaseModel
from uuid import UUID
from api.mixers_dtos import mixerDTO, mixerCutDTO, mixerInputDTO, mixerInputsDTO, mixerSlotDTO, mixerCutProgramDTO, mixerRemoveSlotDTO
from api.auth import require_role
from pipelines.base import GSTBase

router = APIRouter(prefix="/api")


@router.post("/mixer/cut_program", dependencies=[require_role("user")])
async def action_cut_program(request: Request, data: mixerCutProgramDTO):
    handler: GSTBase = request.app.state.pipeline_handler
    program = handler.get_program()
    if not program:
        raise HTTPException(status_code=404, detail="No program mixer")
    response = await program.cut_program(data)
    return response


@router.post("/mixer/add_source", dependencies=[require_role("user")])
async def action_add_source(request: Request, data: mixerCutDTO):
    handler: GSTBase = request.app.state.pipeline_handler
    mixer = handler.get_pipeline("mixers", data.target)
    if not mixer:
        raise HTTPException(status_code=404, detail=f"Mixer {data.target} not found")
    response = mixer.add_source(data)
    return response

@router.post("/mixer/remove_source", dependencies=[require_role("user")])
async def action_remove_source(request: Request, data: mixerCutDTO):
    handler: GSTBase = request.app.state.pipeline_handler
    mixer = handler.get_pipeline("mixers", data.target)
    if not mixer:
        raise HTTPException(status_code=404, detail=f"Mixer {data.target} not found")
    response = mixer.remove_source(data)
    return response

@router.post("/mixer/add_slot", dependencies=[require_role("supervisor")])
async def action_add_slot(request: Request, data: mixerSlotDTO):
    handler: GSTBase = request.app.state.pipeline_handler
    mixer = handler.get_pipeline("mixers", data.uid)
    if not mixer:
        raise HTTPException(status_code=404, detail=f"Mixer {data.uid} not found")
    response = mixer.add_slot(data.slot)
    return response

@router.post("/mixer/remove_slot", dependencies=[require_role("supervisor")])
async def action_remove_slot(request: Request, data: mixerRemoveSlotDTO):
    handler: GSTBase = request.app.state.pipeline_handler
    mixer = handler.get_pipeline("mixers", data.uid)
    if not mixer:
        raise HTTPException(status_code=404, detail=f"Mixer {data.uid} not found")
    inputDTO: mixerInputDTO = mixer.data.getMixerInputDTO(data.index)
    response = mixer.remove_slot(inputDTO)
    return response


@router.patch("/mixers", dependencies=[require_role("user")])
async def update_mixer(request: Request):
    raw = await request.json()
    uid = raw.get('uid')
    if not uid:
        raise HTTPException(status_code=422, detail="uid required")
    handler: GSTBase = request.app.state.pipeline_handler
    mixer = handler.get_pipeline("mixers", UUID(uid))
    if not mixer:
        raise HTTPException(status_code=404, detail=f"Mixer {uid} not found")
    await mixer.update(raw)
    return {"uid": uid}
