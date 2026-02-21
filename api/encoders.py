from fastapi import APIRouter, HTTPException, Request
from uuid import UUID

from api.encoder_models import EncoderEntityDTO
from api.auth import require_role
from api.helper import get_auto_encoder, _is_encoder_available, create_or_raise
from event_loop_bridge import safe_broadcast
from pipelines.encoders.encoder import Encoder

router = APIRouter()


@router.put("/encoders", dependencies=[require_role("outputs")])
async def create_encoder(request: Request, data: EncoderEntityDTO):
    handler = request.app.state._state["pipeline_handler"]

    # Resolve "auto" element
    if data.element == "auto":
        resolved = get_auto_encoder(data.codec)
        if not resolved:
            raise HTTPException(status_code=422, detail=f"No available encoder for codec {data.codec}")
        data.element = resolved

    # Check encoder availability
    if not _is_encoder_available(data.element):
        raise HTTPException(status_code=422, detail=f"Encoder element {data.element} not available")

    existing = handler.get_pipeline("encoders", data.uid)
    if existing:
        existing.data = data
        safe_broadcast("UPDATE", data)
    else:
        encoder = Encoder(data=data)
        await create_or_raise(handler, encoder)

    return {"uid": data.uid}


@router.get("/encoders", dependencies=[require_role("user")])
async def list_encoders(request: Request):
    handler = request.app.state._state["pipeline_handler"]
    encoders = handler.get_pipelines("encoders")
    if not encoders:
        return []
    return [e.describe() for e in encoders]


@router.get("/encoders/{uid}", dependencies=[require_role("user")])
async def get_encoder(uid: UUID, request: Request):
    handler = request.app.state._state["pipeline_handler"]
    encoder = handler.get_pipeline("encoders", uid)
    if not encoder:
        raise HTTPException(status_code=404, detail="Encoder not found")
    return encoder.describe()


@router.delete("/encoders/{uid}", dependencies=[require_role("outputs")])
async def delete_encoder(uid: UUID, request: Request):
    handler = request.app.state._state["pipeline_handler"]
    encoder = handler.get_pipeline("encoders", uid)
    if not encoder:
        raise HTTPException(status_code=404, detail="Encoder not found")

    # Check if any output uses this encoder
    for output in (handler.get_pipelines("outputs") or []):
        if getattr(output, '_video_encoder_uid', None) == uid or \
           getattr(output, '_audio_encoder_uid', None) == uid:
            raise HTTPException(status_code=409, detail=f"Encoder is used by output \"{output.data.name}\". Remove the output first.")

    handler.delete_pipeline("encoders", uid)
    return {"uid": uid}
