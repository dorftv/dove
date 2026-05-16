import asyncio
import base64
from datetime import datetime, timezone
from fastapi import APIRouter
from dove.logger import logger
from dove.proxy.helper import fetch_proxy_items

router = APIRouter()


@router.get("/proxy/ovenmedia")
async def proxy_get():
    async def fetcher(name, details, client):
        headers = {}
        if 'auth' in details:
            base64_auth = base64.b64encode(details['auth'].encode('ascii')).decode('ascii')
            headers['Authorization'] = f'Basic {base64_auth}'

        template = details.get('url_template')
        if not template:
            logger.log(f"proxy/ovenmedia/{name}: missing url_template", level='ERROR')
            return []

        async def fetch_apps(vhost):
            r = await client.get(f"{details['url']}/vhosts/{vhost}/apps", headers=headers)
            r.raise_for_status()
            data = r.json()
            if data.get('statusCode') == 200 and isinstance(data.get('response'), list):
                return vhost, data['response']
            return vhost, []

        async def fetch_streams(vhost, app):
            r = await client.get(f"{details['url']}/vhosts/{vhost}/apps/{app}/streams", headers=headers)
            r.raise_for_status()
            data = r.json()
            if data.get('statusCode') == 200 and isinstance(data.get('response'), list):
                return vhost, app, data['response']
            return vhost, app, []

        vhosts_r = await client.get(f"{details['url']}/vhosts", headers=headers)
        vhosts_r.raise_for_status()
        vhosts_data = vhosts_r.json()
        if not (vhosts_data.get('statusCode') == 200 and isinstance(vhosts_data.get('response'), list)):
            return []
        vhosts = vhosts_data['response']

        apps_results = await asyncio.gather(*[fetch_apps(v) for v in vhosts])

        stream_tasks = [
            fetch_streams(vhost, app)
            for vhost, apps in apps_results
            for app in apps
        ]
        streams_results = await asyncio.gather(*stream_tasks)

        results = []
        for vhost, app, streams in streams_results:
            for stream in streams:
                # operator pins rendition + protocol in the template, e.g. srt://host:port?streamid={vhost}/{app}/{stream}/1080
                try:
                    url = template.format(vhost=vhost, app=app, stream=stream)
                except (KeyError, ValueError) as e:
                    raise ValueError(f"proxy/ovenmedia/{name}: bad url_template '{template}': {e}")
                results.append({
                    "name": f"{name} | {vhost}/{app}/{stream}",
                    "url": url,
                    "clients": 0,
                    "created": datetime.now(timezone.utc).isoformat(),
                })
        return results

    return await fetch_proxy_items("ovenmedia", fetcher)
