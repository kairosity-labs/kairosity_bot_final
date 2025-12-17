import os
import asyncio
import httpx
from typing import List, Dict, Any
from .base import BaseDataMCP


class PerplexitySearchMCP(BaseDataMCP):
    """
    Perplexity Search MCP - Raw ranked search results with advanced filtering.
    
    Uses Perplexity's Search API for structured web results. Returns raw search
    results (title, URL, snippet, date) without AI synthesis.
    
    Best for: Research, multiple sources analysis, precise filtering.
    Cost: Most efficient (no model usage, pure search).
    """
    # Semaphore - lazily initialized to avoid event loop issues with nest_asyncio
    _semaphore_instance = None
    
    @property
    def _semaphore(self):
        if PerplexitySearchMCP._semaphore_instance is None:
            PerplexitySearchMCP._semaphore_instance = asyncio.Semaphore(5)
        return PerplexitySearchMCP._semaphore_instance
    
    def __init__(self, api_key: str = None, max_retries: int = 3, **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = self.api_key or os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/search"
        self.max_retries = max_retries

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perplexity Search API - Raw ranked search results.
        
        Args:
            query (str): Search query string
                
        Returns:
            List of dicts with title, url, content, date, source
        """
        if not query:
            return []
            
        # Use semaphore for rate limiting
        async with self._semaphore:
            # Retry with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }
                    
                    # Optimal defaults for forecasting research
                    payload = {
                        "query": query,
                        "max_results": 10,  # Good coverage
                        "max_tokens_per_page": 2048,  # Expanded content per result
                        "search_recency_filter": "month"  # Focus on recent, relevant data
                    }
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(self.base_url, json=payload, headers=headers)
                        
                        if response.status_code != 200:
                            error_msg = f"Perplexity Search API Error {response.status_code}: {response.text}"
                            
                            # Rate limit handling
                            if response.status_code == 429:
                                if attempt < self.max_retries - 1:
                                    wait_time = 2 ** (attempt + 1)
                                    print(f"Perplexity Search rate limit hit. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                                    await asyncio.sleep(wait_time)
                                    continue
                            
                            raise Exception(error_msg)
                        
                        data = response.json()
                        
                        # Parse results into consistent format
                        results = []
                        for item in data.get("results", []):
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "content": item.get("snippet", ""),
                                "date": item.get("date"),
                                "last_updated": item.get("last_updated"),
                                "source": "perplexity_search"
                            })
                        
                        return results
                        
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "rate limit" in error_str.lower():
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** (attempt + 1)
                            print(f"Perplexity Search rate limit detected. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                    raise
            
            raise Exception(f"Perplexity Search failed after {self.max_retries} retries")
