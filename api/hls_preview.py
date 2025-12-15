from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.responses import FileResponse
import os

from config_handler import ConfigReader

router = APIRouter()

config = ConfigReader()
base_dir = config.get_hls_path()
_base_dir_real = os.path.realpath(base_dir)

@router.get("/preview/hls/{file_path:path}")
async def serve_media(file_path: str):

    full_path = os.path.realpath(os.path.join(base_dir, file_path))
    if not full_path.startswith(_base_dir_real + os.sep):
        return JSONResponse({"error": "Invalid path"}, status_code=400)
    if not os.path.isfile(full_path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    if file_path.endswith(".m3u8"):
        return FileResponse(full_path, media_type="application/x-mpegURL")
    elif file_path.endswith(".ts"):
        return FileResponse(full_path, media_type="video/MP2T")
    else:
        return FileResponse(full_path)
