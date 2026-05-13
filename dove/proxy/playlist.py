from fastapi import APIRouter
from dove.proxy.helper import fetch_proxy_items

router = APIRouter()


@router.get("/proxy/playlist")
async def proxy_get():
    async def fetcher(name, details, client):
        r = await client.get(details['url'])
        r.raise_for_status()
        data = r.json()
        return [{'name': k, 'url': v} for k, v in data.items()]

    return await fetch_proxy_items("playlist", fetcher)
