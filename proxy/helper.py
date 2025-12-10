import httpx
from config_handler import ConfigReader
from logger import logger

config = ConfigReader()


async def fetch_proxy_items(proxy_type, fetcher_fn):
    """Generic async proxy fetcher.

    Reads all configured endpoints for proxy_type, calls fetcher_fn for each,
    merges results. Single httpx.AsyncClient shared across all endpoints.

    Args:
        proxy_type: Config key (e.g., 'srtrelay', 'playlist')
        fetcher_fn: async def(name, details, client) -> list[dict]
    """
    names = config.get_proxy(proxy_type)
    results = []
    async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
        for name in names:
            details = config.get_proxy_details(proxy_type, name)
            if not details or not isinstance(details, dict):
                continue
            try:
                items = await fetcher_fn(name, details, client)
                if items:
                    results.extend(items)
            except httpx.HTTPError as e:
                logger.log(f"proxy/{proxy_type}/{name}: {e}", level='WARNING')
            except Exception as e:
                logger.log(f"proxy/{proxy_type}/{name}: {e}", level='ERROR')
    return results
