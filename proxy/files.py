import os
from fastapi import APIRouter
from config_handler import ConfigReader

router = APIRouter()
config = ConfigReader()


@router.get("/proxy/files")
def proxy_files_get():
    return _scan_files("files", uri_prefix="file://")


@router.get("/proxy/images")
def proxy_images_get():
    return _scan_files("images")


def _scan_files(proxy_name: str, uri_prefix: str = ""):
    details = config.get_config().get("proxy", {}).get(proxy_name, {})
    paths = details.get("paths", [])
    extensions = details.get("extensions", [])

    if isinstance(paths, str):
        paths = [paths]
    if isinstance(extensions, str):
        extensions = [extensions]

    ext_set = {e.lower().lstrip(".") for e in extensions}
    results = []

    for base_path in paths:
        if not os.path.isdir(base_path):
            continue
        for root, _, files in os.walk(base_path):
            for f in sorted(files):
                if ext_set and f.rsplit(".", 1)[-1].lower() not in ext_set:
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, base_path)
                results.append({"name": rel, "url": f"{uri_prefix}{full}"})

    results.sort(key=lambda x: x["name"])
    return results
