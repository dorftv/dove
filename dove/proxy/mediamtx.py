from datetime import datetime, timezone
from fastapi import APIRouter
from dove.proxy.helper import fetch_proxy_items

router = APIRouter()


@router.get("/proxy/mediamtx")
async def proxy_get():
    async def fetcher(name, details, client):
        r = await client.get(details['url'])
        r.raise_for_status()
        data = r.json()
        res = []
        if isinstance(data, dict) and 'items' in data:
            for item in data['items']:
                stream_name = item['name']
                auth_string = f"{details['user']}:{details['pass']}"
                res.append({
                    "name": f"{name}/{stream_name}",
                    "url": f"{details['base_url']}?streamid=read:{stream_name}:{auth_string}",
                    "clients": len(item.get('readers', [])),
                    "created": item.get('readyTime') or datetime.now(timezone.utc).isoformat(),
                })
        return res

    return await fetch_proxy_items("mediamtx", fetcher)
