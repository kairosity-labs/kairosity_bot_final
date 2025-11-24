from typing import List, Dict, Any
from .base import BaseDataMCP
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

class DuckDuckGoMCP(BaseDataMCP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if DDGS is None:
            raise ImportError("duckduckgo-search package is required for DuckDuckGoMCP")

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        max_results = kwargs.get("limit", 5)
        results = []
        
        # DDGS is synchronous, so we might want to run it in a thread executor if we want true async,
        # but for now we'll keep it simple or assume it's fast enough.
        # To be proper async, we should use run_in_executor.
        import asyncio
        from functools import partial
        
        def _search_sync():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        loop = asyncio.get_event_loop()
        ddg_results = await loop.run_in_executor(None, _search_sync)
        
        for res in ddg_results:
            results.append({
                "title": res.get("title"),
                "content": res.get("body"),
                "url": res.get("href"),
                "source": "duckduckgo"
            })
        return results
