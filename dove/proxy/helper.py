import httpx
from dove.config_handler import ConfigReader
from dove.logger import logger

config = ConfigReader()


async def fetch_proxy_items(proxy_type, fetcher_fn):
    """Generic async proxy fetcher: calls fetcher_fn for each configured endpoint, merges results."""
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
