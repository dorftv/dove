# main.py
from fastapi import Request, APIRouter
from api.mixer_dtos import mixerDTO, mixerInputDTO, mixerInputsDTO
from pipelines.base import GSTBase

router = APIRouter(prefix="/api")

@router.post("/cut")
async def action_cut(request: Request, item: mixerDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixerInput = mixerInputDTO(src=item.src)
    mixerInputs = mixerInputsDTO(target=item.target, src=[mixerInput])
    mixer = handler.get_pipeline("mixers", item.target)
    mixer.cut(mixerInputs)
    return {"src": item.src, "target": item.target}
