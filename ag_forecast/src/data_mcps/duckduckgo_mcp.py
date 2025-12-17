import asyncio
from typing import List, Dict, Any
from .base import BaseDataMCP
try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

class DuckDuckGoMCP(BaseDataMCP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if DDGS is None:
            raise ImportError("duckduckgo-search package is required for DuckDuckGoMCP")
        
        if not hasattr(self, '_semaphore'):
            self._semaphore = asyncio.Semaphore(5) # Default concurrency limit

    async def search(self, query: str) -> List[Dict[str, Any]]:
        if not query:
            return []
        
        # Hardcoded defaults
        max_results = 10
        def _search_sync():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        loop = asyncio.get_event_loop()
        ddg_results = await loop.run_in_executor(None, _search_sync)
        
        results = []
        for res in ddg_results:
            results.append({
                "title": res.get("title"),
                "content": res.get("body"),
                "url": res.get("href"),
                "source": "duckduckgo"
            })
        return results
