from fastapi import APIRouter
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse
from datetime import datetime, timezone

from config_handler import ConfigReader

config = ConfigReader()
router = APIRouter()

@router.get("/proxy/mediamtx")
def proxy_get():
    relay_names = config.get_proxy("mediamtx")

    def fetch_url(name):
        details = config.get_proxy_details("mediamtx", name)
        if not details or not isinstance(details, dict):
            return []
        try:
            response = requests.get(details['url'], timeout=5)
            response.raise_for_status()
            data = response.json()

            res = []
            if isinstance(data, dict) and 'items' in data:
                for item in data['items']:
                    stream_name = item['name']
                    auth_string = f"{details['user']}:{details['pass']}"
                    url = f"{details['base_url']}?streamid=read:{stream_name}:{auth_string}"

                    new_item = {
                        "name": f"{name}/{stream_name}",
                        "url": url,
                        "clients": len(item.get('readers', [])),
                        "created": item.get('readyTime') or datetime.now(timezone.utc).isoformat()
                    }
                    res.append(new_item)
            return res
        except requests.RequestException:
            return []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_url, name) for name in relay_names]
        merged_results = []
        for future in as_completed(futures):
            data = future.result()
            if data:
                merged_results.extend(data)

    return merged_results