import base64
from datetime import datetime, timezone
from fastapi import APIRouter
from proxy.helper import fetch_proxy_items

router = APIRouter()


@router.get("/proxy/ovenmedia")
async def proxy_get():
    async def fetcher(name, details, client):
        headers = {}
        if 'auth' in details:
            base64_auth = base64.b64encode(details['auth'].encode('ascii')).decode('ascii')
            headers['Authorization'] = f'Basic {base64_auth}'

        stream_type = details.get('type', 'srt').lower()

        vhosts_r = await client.get(f"{details['url']}/vhosts", headers=headers)
        vhosts_r.raise_for_status()
        vhosts_data = vhosts_r.json()

        results = []
        if vhosts_data.get('statusCode') == 200 and isinstance(vhosts_data.get('response'), list):
            for vhost in vhosts_data['response']:
                apps_r = await client.get(f"{details['url']}/vhosts/{vhost}/apps", headers=headers)
                apps_r.raise_for_status()
                apps_data = apps_r.json()

                if apps_data.get('statusCode') == 200 and isinstance(apps_data.get('response'), list):
                    for app in apps_data['response']:
                        streams_r = await client.get(f"{details['url']}/vhosts/{vhost}/apps/{app}/streams", headers=headers)
                        streams_r.raise_for_status()
                        streams_data = streams_r.json()

                        if streams_data.get('statusCode') == 200 and isinstance(streams_data.get('response'), list):
                            for stream in streams_data['response']:
                                if stream_type == 'webrtc':
                                    url = f"{details['base_url']}/{vhost}/{app}/{stream}"
                                elif stream_type == 'llhls':
                                    url = f"{details['base_url']}/{vhost}/{app}/{stream}/index.m3u8"
                                else:
                                    url = f"{details['base_url']}?streamid={vhost}/{app}/{stream}"

                                results.append({
                                    "name": f"{name}/{vhost}/{app}/{stream}",
                                    "url": url,
                                    "clients": 0,
                                    "created": datetime.now(timezone.utc).isoformat(),
                                })
        return results

    return await fetch_proxy_items("ovenmedia", fetcher)
