from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(prefix="/preview")

@router.get("/hls/{source_name}")
async def playlist(source_name: str):
    playlist_path = Path("/var/dove/hls").joinpath(source_name, "index.m3u8")
    return FileResponse(playlist_path, media_type="application/x-mpegURL")
