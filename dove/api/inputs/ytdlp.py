
import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field
from dove.api.input_models import InputDTO, SuccessDTO
from typing import Optional

import yt_dlp.utils

from dove.config_handler import ConfigReader
from dove.event_loop_bridge import safe_broadcast
from dove.api.helper import create_or_raise
from dove.logger import logger
router = APIRouter()

class YtdlpInputDTO(InputDTO):
    type: str = Field(
        label="Youtube&Co",
        default="ytdlp",
        description="Allows playback from youtube and many other video sites supported by yt-dlp.",
    )
    uri: str = Field(
        label="Uri",
        help="Any Url supported by youtube-dl fork yt-dlp.",
        placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    loop: Optional[bool] = Field(
        label="Loop",
        default=False,
        help="Loop the the file on EOS"
    )

from dove.pipelines.inputs.ytdlp import YtdlpInput, _extract_ytdlp_url


async def _resolve_or_raise(uri: str) -> str:
    height = ConfigReader().get_default_height()
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_extract_ytdlp_url, uri, height),
            timeout=30,
        )
    except asyncio.TimeoutError:
        logger.log(f"ytdlp: timeout resolving {uri}", level='ERROR')
        raise HTTPException(status_code=504, detail=f"ytdlp: timeout resolving {uri}")
    except yt_dlp.utils.UnsupportedError as e:
        raise HTTPException(status_code=400, detail=f"ytdlp: unsupported URL: {e}")
    except yt_dlp.utils.GeoRestrictedError as e:
        raise HTTPException(status_code=451, detail=f"ytdlp: geo-restricted: {e}")
    except yt_dlp.utils.ExtractorError as e:
        raise HTTPException(status_code=422, detail=f"ytdlp: extractor error: {e}")
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=502, detail=f"ytdlp: download failed: {e}")
    except Exception as e:
        logger.log(f"ytdlp: unexpected error resolving {uri}: {e}", level='ERROR')
        raise HTTPException(status_code=500, detail=f"ytdlp: {e}")


@router.put("/ytdlp", response_model=SuccessDTO)
async def create_ytdlp_input(request: Request, data: YtdlpInputDTO):
    handler = request.app.state.pipeline_handler
    resolved = await _resolve_or_raise(data.uri)
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        input._resolved_uri = resolved
        safe_broadcast("UPDATE", data)
    else:
        input = YtdlpInput(data=data)
        input._resolved_uri = resolved
        await create_or_raise(handler, input)

    return data