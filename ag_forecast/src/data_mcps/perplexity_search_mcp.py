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
    
    Kwargs for search():
        - max_results (int): 1-20 results, default 10
        - search_domain_filter (List[str]): Allowlist domains, prefix with '-' for denylist
        - search_recency_filter (str): "day"|"week"|"month"|"year"
        - search_after_date (str): "MM/DD/YYYY" - results after this date
        - search_before_date (str): "MM/DD/YYYY" - results before this date
        - country (str): ISO country code (e.g., "US", "GB")
        - max_tokens_per_page (int): Content extraction limit per result, default 1024
    """
    # Class-level semaphore to limit concurrent requests
    _semaphore = asyncio.Semaphore(3)
    
    def __init__(self, api_key: str = None, max_retries: int = 3, **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = self.api_key or os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/search"
        self.max_retries = max_retries

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Perplexity Search API - Raw ranked search results.
        
        Args:
            query: The search query string
            **kwargs: Optional parameters:
                - max_results (int): 1-20, default 10
                - search_domain_filter (List[str]): Domain filter list
                - search_recency_filter (str): "day"|"week"|"month"|"year"
                - search_after_date (str): "MM/DD/YYYY"
                - search_before_date (str): "MM/DD/YYYY"
                - country (str): ISO country code
                - max_tokens_per_page (int): Content per result, default 1024
                
        Returns:
            List of dicts with title, url, content, date, source
        """
        # Use semaphore for rate limiting
        async with self._semaphore:
            # Retry with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }
                    
                    # Build payload
                    payload = {
                        "query": query,
                        "max_results": kwargs.get("max_results", 10),
                        "max_tokens_per_page": kwargs.get("max_tokens_per_page", 1024),
                    }
                    
                    # Add optional filters
                    if "search_domain_filter" in kwargs:
                        payload["search_domain_filter"] = kwargs["search_domain_filter"]
                    if "search_recency_filter" in kwargs:
                        payload["search_recency_filter"] = kwargs["search_recency_filter"]
                    if "search_after_date" in kwargs:
                        payload["search_after_date"] = kwargs["search_after_date"]
                    if "search_before_date" in kwargs:
                        payload["search_before_date"] = kwargs["search_before_date"]
                    if "country" in kwargs:
                        payload["country"] = kwargs["country"]
                    
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
