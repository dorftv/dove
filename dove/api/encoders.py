from fastapi import APIRouter, HTTPException, Request
from uuid import UUID

from dove.api.encoder_models import EncoderEntityDTO
from dove.api.auth import require_role, require_read
from dove.api.helper import get_auto_encoder, _is_encoder_available, create_or_raise
from dove.event_loop_bridge import safe_broadcast
from dove.pipelines.encoders.encoder import Encoder

router = APIRouter()


@router.put("/encoders", dependencies=[require_role("outputs")])
async def create_encoder(request: Request, data: EncoderEntityDTO):
    handler = request.app.state.pipeline_handler

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


@router.get("/encoders", dependencies=[require_read()])
async def list_encoders(request: Request):
    handler = request.app.state.pipeline_handler
    encoders = handler.get_pipelines("encoders")
    if not encoders:
        return []
    return [e.describe() for e in encoders]


@router.get("/encoders/{uid}", dependencies=[require_read()])
async def get_encoder(uid: UUID, request: Request):
    handler = request.app.state.pipeline_handler
    encoder = handler.get_pipeline("encoders", uid)
    if not encoder:
        raise HTTPException(status_code=404, detail="Encoder not found")
    return encoder.describe()


@router.delete("/encoders/{uid}", dependencies=[require_role("outputs")])
async def delete_encoder(uid: UUID, request: Request):
    handler = request.app.state.pipeline_handler
    encoder = handler.get_pipeline("encoders", uid)
    if not encoder:
        raise HTTPException(status_code=404, detail="Encoder not found")

    # Preview encoders are cascade-deleted via their upstream input/scene/mixer.
    if getattr(encoder.data, 'is_preview', False):
        raise HTTPException(status_code=403, detail="Preview encoders are removed only via their upstream input/scene/mixer.")

    # Reject if any output still references this encoder.
    refs = [o for o in (handler.get_pipelines("outputs") or [])
            if getattr(o.data, 'video_encoder', None) == uid or getattr(o.data, 'audio_encoder', None) == uid]
    if refs:
        raise HTTPException(status_code=409, detail=f"Encoder in use by {len(refs)} output(s)")

    handler.delete_pipeline("encoders", uid)
    return {"uid": uid}
