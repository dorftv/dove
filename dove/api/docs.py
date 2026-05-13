from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, JSONResponse, FileResponse
import os

router = APIRouter(prefix="/api")

docs_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs"))


@router.get("/docs/{slug}.md")
async def get_doc(slug: str):
    path = os.path.realpath(os.path.join(docs_dir, f"{slug}.md"))
    if not path.startswith(docs_dir + os.sep):
        return JSONResponse({"error": "Invalid slug"}, status_code=400)
    if not os.path.isfile(path):
        return JSONResponse({"error": "Not found"}, status_code=404)

    with open(path) as f:
        return PlainTextResponse(f.read(), media_type="text/markdown")


@router.get("/docs/images/{filename}")
async def get_doc_image(filename: str):
    images_dir = os.path.join(docs_dir, "images")
    path = os.path.realpath(os.path.join(images_dir, filename))
    if not path.startswith(os.path.realpath(images_dir) + os.sep):
        return JSONResponse({"error": "Invalid filename"}, status_code=400)
    if not os.path.isfile(path):
        return JSONResponse({"error": "Not found"}, status_code=404)

    return FileResponse(path)
