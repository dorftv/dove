from fastapi import APIRouter
from starlette.responses import FileResponse
import os

router = APIRouter()

# Base directory for media files
base_dir = "/var/dove/hls"

@router.get("/preview/hls/{file_path:path}")
async def serve_media(file_path: str):

    full_path = os.path.join(base_dir, file_path)
    if not os.path.isfile(full_path):
        return {"error": "File not found"}

    if file_path.endswith(".m3u8"):
        return FileResponse(full_path, media_type="application/x-mpegURL")
    elif file_path.endswith(".ts"):
        return FileResponse(full_path, media_type="video/MP2T")
    else:
        return FileResponse(full_path)
