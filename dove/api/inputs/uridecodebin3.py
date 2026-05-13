
from fastapi import APIRouter, Request, HTTPException
from pydantic import Field
from dove.api.input_models import InputDTO, SuccessDTO
from typing import Optional
from dove.event_loop_bridge import safe_broadcast
from dove.api.helper import create_or_raise
from urllib.parse import urlparse
import httpx

router = APIRouter()

_REJECTED_TYPES = ("text/html", "application/xhtml+xml")
_ALLOWED_MEDIA_TYPES = ("application/vnd.apple.mpegurl", "application/x-mpegurl",
                        "application/dash+xml", "audio/mpegurl")
_MEDIA_EXTENSIONS = (
    '.mp3', '.mp4', '.aac', '.ogg', '.opus', '.m4a', '.flac',
    '.wav', '.mpd', '.m3u8', '.ts', '.mkv', '.webm', '.mov',
)

async def check_uri_content_type(uri: str, timeout: float = 3.0) -> str | None:
    """Return rejection reason if HTTP URI serves HTML, or None if acceptable."""
    if not uri or not uri.lower().startswith(("http://", "https://")):
        return None
    path = urlparse(uri).path.lower().rstrip('/')
    if any(path.endswith(ext) for ext in _MEDIA_EXTENSIONS):
        return None  # trust explicit media extension
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.head(uri)
            ct = resp.headers.get("content-type", "").lower().split(";")[0].strip()
            if ct in _ALLOWED_MEDIA_TYPES:
                return None
            if any(ct.startswith(r) for r in _REJECTED_TYPES):
                return f"URI serves {ct}, not media content"
    except Exception:
        pass  # Timeout, network error, 405 — fail open
    return None


class Uridecodebin3InputDTO(InputDTO):
    type: str = Field(
        label="Streams/Videos",
        default="uridecodebin3",
        description="Plays local and remote files and streams via uridecodebin3.",
    )
    uri: str = Field(
        label="Uri",
        description="Enter Uri to play",
        help="eg: file:/// | http://  | rtmp:// | srt://",
        placeholder="file:///home/user/video.mp4",
    )
    loop: Optional[bool] = Field(
        label="Loop",
        default=False,
        help="Loop the the file on EOS"
    )


from dove.pipelines.inputs.uridecodebin3 import Uridecodebin3Input

@router.put("/uridecodebin3", response_model=SuccessDTO)
@router.put("/playbin3", response_model=SuccessDTO, include_in_schema=False)
async def create_uridecodebin3_input(request: Request, data: Uridecodebin3InputDTO):
    reason = await check_uri_content_type(data.uri)
    if reason:
        raise HTTPException(status_code=422, detail=reason)

    handler = request.app.state.pipeline_handler
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = Uridecodebin3Input(data=data)
        await create_or_raise(handler, input)

    return data
