
from fastapi import APIRouter, Request, HTTPException
from pydantic import Field
from api.input_models import InputDTO, SuccessDTO
from typing import Optional
from helpers import get_default_height, get_default_width
from event_loop_bridge import safe_broadcast
from api.helper import create_or_raise

router = APIRouter()

_ALLOWED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".svg")


class ImagesrcInputDTO(InputDTO):
    type: str = Field(
        label="Image/Still",
        default="imagesrc",
        description="Renders still images with minimal overhead.",
    )
    location: str = Field(
        label="Location",
        description="Path to image file",
        help="Supported: PNG, JPEG, BMP, WebP, SVG",
        placeholder="/videos/logo.png",
    )
    show_controls: bool = False
    height: Optional[int] = Field(default_factory=get_default_height)
    width: Optional[int] = Field(default_factory=get_default_width)


from pipelines.inputs.imagesrc import ImagesrcInput


@router.put("/imagesrc", response_model=SuccessDTO)
async def create_imagesrc_input(request: Request, data: ImagesrcInputDTO):
    if not any(data.location.lower().endswith(ext) for ext in _ALLOWED_EXTENSIONS):
        raise HTTPException(422, f"Unsupported file type. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}")

    handler = request.app.state._state["pipeline_handler"]
    input = handler.get_pipeline("inputs", data.uid)

    if input:
        input.data = data
        safe_broadcast("UPDATE", data)
    else:
        input = ImagesrcInput(data=data)
        await create_or_raise(handler, input)

    return data
