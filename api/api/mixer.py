# main.py
from fastapi import FastAPI, APIRouter
from api.mixer_dtos import mixerDTO

router = APIRouter(prefix="/api")

@router.post("/cut")
async def action_cut(item: mixerDTO):
    return {"src": item.src, "target": item.target}