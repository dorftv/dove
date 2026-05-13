from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.responses import FileResponse
import os

from dove.api.auth import get_current_user_optional, is_auth_enabled
from dove.config_handler import ConfigReader

router = APIRouter()

config = ConfigReader()
base_dir = config.get_hls_path()
_base_dir_real = os.path.realpath(base_dir)

@router.get("/preview/hls/{file_path:path}")
async def serve_media(file_path: str, request: Request):
    if is_auth_enabled():
        user = await get_current_user_optional(request)
        if user is None:
            # HLS path convention: {source_uid}/{playlist_or_segment}
            source_uid = file_path.split('/')[0]
            handler = request.app.state.pipeline_handler
            entity = handler.get_pipeline_by_uid(source_uid)
            if not entity or not config.is_public_preview(entity.data.name):
                raise HTTPException(status_code=401, detail="Not authenticated")

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
