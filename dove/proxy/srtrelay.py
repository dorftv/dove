import urllib.parse
from fastapi import APIRouter
from dove.proxy.helper import fetch_proxy_items

router = APIRouter()


@router.get("/proxy/srtrelay")
async def proxy_get():
    async def fetcher(name, details, client):
        r = await client.get(details['url'])
        r.raise_for_status()
        data = r.json()
        res = []
        if isinstance(data, list):
            for item in data:
                if 'url' in item:
                    item['url'] = f"{item['url']}/{urllib.parse.quote(details.get('auth', ''))}"
                if 'name' in item:
                    item['name'] = f"{name}/{item['name']}"
                res.append(item)
        return res

    return await fetch_proxy_items("srtrelay", fetcher)
