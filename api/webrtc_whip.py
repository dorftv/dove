"""
WHIP ingest server for WebRTC screen sharing / camera input.

Endpoints mirror the WHEP pattern:
  POST   /whip/ingest/{input_uid}           — receive SDP offer, return answer
  PATCH  /whip/ingest/resource/{resource_id} — trickle ICE candidates
  DELETE /whip/ingest/resource/{resource_id} — disconnect publisher
  OPTIONS                                    — CORS preflight
"""

import asyncio
import uuid
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request, Response

from api.webrtc_utils import get_host_ip
from event_loop_bridge import bridge
from logger import logger

router = APIRouter()

# resource_id -> (input_uid_str, WhipInput ref)
_resources: dict[str, tuple[str, object]] = {}


def _find_whip_input(input_uid: str):
    """Look up the WhipInput pipeline component by UID string."""
    from pipeline_handler import HandlerSingleton
    handler = HandlerSingleton()
    try:
        uid = UUID(input_uid)
    except ValueError:
        return None
    inp = handler.get_pipeline("inputs", uid)
    if inp and hasattr(inp, 'connect_publisher'):
        return inp
    return None


def remove_resources_for_input(input_uid: str):
    """Clean up resource entries for a disconnected input (called from pipeline code)."""
    stale = [rid for rid, (uid, _) in _resources.items() if uid == input_uid]
    for rid in stale:
        _resources.pop(rid, None)


@router.post("/whip/ingest/{input_uid}")
async def whip_offer(input_uid: str, request: Request):
    content_type = request.headers.get("content-type", "")
    if "application/sdp" not in content_type:
        return Response(status_code=400, content="Content-Type must be application/sdp")

    if int(request.headers.get('content-length', 0)) > 65536:
        raise HTTPException(status_code=413, detail="Payload too large")

    whip_input = _find_whip_input(input_uid)
    if not whip_input:
        return Response(status_code=404, content="Input not found or not a WHIP input")

    if not whip_input.try_claim():
        return Response(status_code=409, content="Publisher already connected")

    try:
        sdp_offer = (await request.body()).decode("utf-8")
        host_ip = get_host_ip(request)
        resource_id = str(uuid.uuid4())
        _resources[resource_id] = (input_uid, whip_input)

        loop = asyncio.get_running_loop()
        answer_future = loop.create_future()
        whip_input.connect_publisher(sdp_offer, answer_future, loop, host_ip)

        try:
            answer = await asyncio.wait_for(answer_future, timeout=10.0)
        except asyncio.TimeoutError:
            _resources.pop(resource_id, None)
            # Full teardown via the GLib thread — clears _publisher_pipeline,
            # _publisher_webrtcbin and _publisher_claimed via the tested
            # READY → flush → remove → NULL → orphan sequence. Awaited so the
            # claim is fully released before the 500 response goes out;
            # disconnect_publisher early-returns safely if setup failed before
            # _publisher_pipeline was assigned.
            try:
                await bridge.call_glib_async(whip_input.disconnect_publisher)
            except Exception as e:
                logger.log(f"WHIP cleanup error after failure: {e}", level='WARNING')
            return Response(status_code=500, content="WebRTC session setup timed out")

        if not answer:
            _resources.pop(resource_id, None)
            try:
                await bridge.call_glib_async(whip_input.disconnect_publisher)
            except Exception as e:
                logger.log(f"WHIP cleanup error after failure: {e}", level='WARNING')
            return Response(status_code=500, content="Failed to create WebRTC session")

        return Response(
            status_code=201, content=answer, media_type="application/sdp",
            headers={
                "Location": f"/whip/ingest/resource/{resource_id}",
                "Access-Control-Expose-Headers": "Location",
            },
        )
    except Exception as e:
        logger.log(f"WHIP offer error: {e}", level='ERROR')
        rid = locals().get('resource_id')
        if rid:
            _resources.pop(rid, None)
        try:
            await bridge.call_glib_async(whip_input.disconnect_publisher)
        except Exception as e:
            logger.log(f"WHIP cleanup error after failure: {e}", level='WARNING')
        return Response(status_code=500, content="WHIP offer handler error")


@router.patch("/whip/ingest/resource/{resource_id}")
async def whip_ice_candidate(resource_id: str, request: Request):
    if resource_id not in _resources:
        return Response(status_code=404)

    _, whip_input = _resources[resource_id]
    content_type = request.headers.get("content-type", "")

    if "application/trickle-ice-sdpfrag" in content_type:
        if int(request.headers.get('content-length', 0)) > 65536:
            raise HTTPException(status_code=413, detail="Payload too large")
        body = (await request.body()).decode("utf-8")
        # Note: a=mid: is technically a string, but browsers use numeric indices.
        # Falls back to 0 if non-numeric (safe for video-only streams).
        sdp_mline_index = 0
        for line in body.strip().split("\n"):
            line = line.strip()
            if line.startswith("a=mid:"):
                try:
                    sdp_mline_index = int(line[6:])
                except ValueError:
                    pass
        for line in body.strip().split("\n"):
            line = line.strip()
            if line.startswith("a=ice-candidate:"):
                candidate = line[2:]

                def do_add(c=candidate, idx=sdp_mline_index):
                    whip_input.add_ice_candidate(idx, c)

                bridge.run_sync_in_glib(do_add)

    return Response(status_code=204)


@router.delete("/whip/ingest/resource/{resource_id}")
async def whip_delete(resource_id: str):
    mapping = _resources.pop(resource_id, None)
    if not mapping:
        return Response(status_code=404)

    _, whip_input = mapping
    loop = asyncio.get_running_loop()
    done = loop.create_future()

    def do_disconnect():
        try:
            whip_input.disconnect_publisher()
        except Exception as e:
            logger.log(f"WHIP delete error: {e}", level='ERROR')
        loop.call_soon_threadsafe(done.set_result, True)

    bridge.run_sync_in_glib(do_disconnect)
    await done
    return Response(status_code=200)


@router.options("/whip/ingest/{input_uid}")
@router.options("/whip/ingest/resource/{resource_id}")
async def whip_options(input_uid: str = "", resource_id: str = ""):
    return Response(status_code=200, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })
