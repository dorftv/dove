from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def ui():
    with open("static/index.html", "r") as f:
        return f.read()