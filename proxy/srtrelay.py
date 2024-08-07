from fastapi import APIRouter
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse

from config_handler import ConfigReader

config = ConfigReader()
router = APIRouter()

@router.get("/proxy/srtrelay")
def proxy_get():
    relay_names = config.get_proxy("srtrelay")

    def fetch_url(name):
        details = config.get_proxy_details("srtrelay", name)
        if not details:
            return []
        try:
            if not isinstance(details, dict):
                return []
            print(details)
            response = requests.get(details['url'], timeout=5)
            response.raise_for_status()
            data = response.json()
            res = []
            if isinstance(data, list):
                for item in data:
                    if 'url' in item:
                        item['url'] = f"{item['url']}/{urllib.parse.quote(details['auth'])}"
                    if 'name' in item:
                        item['name'] = f"{name}/{item['name']}"
                    print(item)
                    res.append(item)
            return res
        except requests.RequestException as e:
            return []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_url, name) for name in relay_names]
        merged_results = []
        for future in as_completed(futures):
            data = future.result()
            if data:
                merged_results.extend(data)

    return merged_results