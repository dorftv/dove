from fastapi import APIRouter
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import base64
import logging

from config_handler import ConfigReader

config = ConfigReader()
router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/proxy/ovenmedia")
def proxy_get():
    relay_names = config.get_proxy("ovenmedia")
    logger.info(f"Found relay names: {relay_names}")

    def fetch_url(name):
        details = config.get_proxy_details("ovenmedia", name)
        if not details or not isinstance(details, dict):
            return []
        
        try:
            headers = {}
            if 'auth' in details:
                auth_bytes = details['auth'].encode('ascii')
                base64_auth = base64.b64encode(auth_bytes).decode('ascii')
                headers['Authorization'] = f'Basic {base64_auth}'
            
            stream_type = details.get('type', 'srt').lower()
     
            # Get vhosts (corrected URL)
            vhosts_response = requests.get(
                f"{details['url']}/vhosts", 
                headers=headers, 
                timeout=5
            )
            vhosts_response.raise_for_status()
            vhosts_data = vhosts_response.json()
            logger.info(f"Vhosts response: {vhosts_data}")
            
            results = []
            if vhosts_data.get('statusCode') == 200 and isinstance(vhosts_data.get('response'), list):
                for vhost in vhosts_data['response']:
                    # Get apps for each vhost (corrected URL)
                    apps_response = requests.get(
                        f"{details['url']}/vhosts/{vhost}/apps", 
                        headers=headers,
                        timeout=5
                    )
                    apps_response.raise_for_status()
                    apps_data = apps_response.json()
                    logger.info(f"Apps response for {vhost}: {apps_data}")
                    
                    if apps_data.get('statusCode') == 200 and isinstance(apps_data.get('response'), list):
                        for app in apps_data['response']:
                            # Get streams for each app (corrected URL)
                            streams_response = requests.get(
                                f"{details['url']}/vhosts/{vhost}/apps/{app}/streams", 
                                headers=headers,
                                timeout=5
                            )
                            streams_response.raise_for_status()
                            streams_data = streams_response.json()


                            if streams_data.get('statusCode') == 200 and isinstance(streams_data.get('response'), list):
                                for stream in streams_data['response']:                                    
                                    if stream_type == 'webrtc':
                                        url = f"{details['base_url']}/{vhost}/{app}/{stream}"
                                    elif stream_type == 'llhls':
                                        url = f"{details['base_url']}/{vhost}/{app}/{stream}/index.m3u8"
                                    # default to srt
                                    else:
                                        url = f"{details['base_url']}?streamid={vhost}/{app}/{stream}"

                                    stream_item = {
                                        "name": f"{name}/{vhost}/{app}/{stream}",
                                        "url": url,
                                        "clients": 0,
                                        "created": datetime.now(timezone.utc).isoformat()
                                    }

                                    results.append(stream_item)

            return results
            
        except requests.RequestException as e:
            logger.error(f"Request failed for {name}: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error for {name}: {str(e)}")
            return []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_url, name) for name in relay_names]
        merged_results = []
        for future in as_completed(futures):
            try:
                data = future.result()
                if data:
                    merged_results.extend(data)
            except Exception as e:
                logger.error(f"Error processing future: {str(e)}")

    logger.info(f"Final merged results: {merged_results}")
    return merged_results