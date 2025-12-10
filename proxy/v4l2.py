import glob
import re
from fastapi import APIRouter

router = APIRouter()


@router.get("/proxy/v4l2")
def proxy_get():
    devices = sorted(glob.glob("/dev/video*"))
    return [{"name": d, "url": d} for d in devices]


@router.get("/proxy/alsa")
def proxy_alsa_get():
    """List available ALSA capture devices from /dev/snd."""
    devices = []
    # pcmC{card}D{device}c = capture device
    for path in sorted(glob.glob("/dev/snd/pcmC*c")):
        m = re.search(r"pcmC(\d+)D(\d+)c", path)
        if m:
            card, dev = m.group(1), m.group(2)
            hw = f"hw:{card},{dev}"
            devices.append({"name": hw, "url": hw})
    return devices
