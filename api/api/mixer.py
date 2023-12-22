# main.py
from fastapi import Request, APIRouter
from api.mixer_dtos import mixerDTO
from pipelines.base import GSTBase

router = APIRouter(prefix="/api")

@router.post("/cut")
async def action_cut(request: Request, item: mixerDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    pipeline = handler.get_pipeline_all(item.target)
    pipeline.cut()
    return {"src": item.src, "target": item.target}