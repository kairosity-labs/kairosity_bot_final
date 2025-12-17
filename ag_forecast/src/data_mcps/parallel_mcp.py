import os
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from .base import BaseDataMCP


class ParallelMCP(BaseDataMCP):
    """
    Parallel.ai Unified MCP - Search + Auto-Extraction (Simplified).
    
    Combines search and extraction with fixed defaults:
    - Search: "one-shot" mode, 10 results
    - Extract: Excerpts enabled, Full content disabled
    
    Input: Expects only 'query' in kwargs.
    """
    # Semaphores - lazily initialized to avoid event loop issues with nest_asyncio
    _search_semaphore_instance = None
    _extract_semaphore_instance = None
    
    @property
    def _search_semaphore(self):
        if ParallelMCP._search_semaphore_instance is None:
            ParallelMCP._search_semaphore_instance = asyncio.Semaphore(5)
        return ParallelMCP._search_semaphore_instance
    
    @property
    def _extract_semaphore(self):
        if ParallelMCP._extract_semaphore_instance is None:
            ParallelMCP._extract_semaphore_instance = asyncio.Semaphore(3)
        return ParallelMCP._extract_semaphore_instance
    
    def __init__(self, api_key: str = None, max_retries: int = 3, **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = self.api_key or os.getenv("PARALLEL_API_KEY")
        self.search_url = "https://api.parallel.ai/v1beta/search"
        self.extract_url = "https://api.parallel.ai/v1beta/extract"
        self.max_retries = max_retries

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Unified Search + Extract.
        
        Args:
            query (str): Search query (REQUIRED)
                
        Returns:
            List of dicts with title, url, content (extracted markdown), source
        """
        # query is passed directly now
        if not query:
             return []

        search_results = await self._perform_search(query)
        
        if not search_results:
            return []
            
        # # Extract URLs
        # urls_to_extract = [r['url'] for r in search_results if r.get('url')]
        
        # if not urls_to_extract:
        #     return search_results # Return snippets if no URLs found
            
        # # Batch Extract
        # extracted_data = await self._perform_extract(urls_to_extract, objective=query)
        
        # # Merge Results
        final_results = []
        # for search_item in search_results:
        #     url = search_item.get('url')
        #     # Find matching extraction
        #     extract_item = next((item for item in extracted_data if item.get('url') == url), None)
            
        #     content = ""
        #     if extract_item:
        #         content = extract_item.get('content', '')
        #     else:
        #         content = search_item.get('content', '')
                
        #     final_results.append({
        #         "title": search_item.get("title", ""),
        #         "url": url,
        #         "content": content,
        #         "source": "parallel_mcp"
        #     })

        for search_item in search_results:
            final_results.append({
                "title": search_item.get("title", ""),
                "url": search_item.get("url", ""),
                "content": search_item.get("content", ""),
                "source": "parallel_mcp"
            })
            
        return final_results

    async def _perform_search(self, query: str) -> List[Dict[str, Any]]:
        """Internal search helper with fixed constants"""
        
        async with self._search_semaphore:
            for attempt in range(self.max_retries):
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "parallel-beta": "search-extract-2025-10-10"
                    }
                    
                    # Hardcoded constants as requested
                    payload = {
                        "mode": "one-shot",
                        "search_queries": [query],
                        "max_results": 5
                    }
                    
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(self.search_url, json=payload, headers=headers)
                        
                        if response.status_code == 429:
                             wait_time = 2 ** (attempt + 1)
                             await asyncio.sleep(wait_time)
                             continue
                             
                        if response.status_code != 200:
                            print(f"ERROR: {response.text}")
                            if hasattr(self, 'logger') and self.logger:
                                self.logger.warning(f"Search API Error {response.status_code}: {response.text}")
                            return []

                        data = response.json()
                        results = []
                        for item in data.get("results", []):
                            excerpts = item.get("excerpts", [])
                            snippet_parts = []
                            for e in excerpts:
                                if isinstance(e, str): snippet_parts.append(e)
                                elif isinstance(e, dict): snippet_parts.append(e.get("text", ""))
                            
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("url", ""),
                                "content": " ... ".join(snippet_parts)
                            })
                        return results
                        
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        if hasattr(self, 'logger') and self.logger:
                            self.logger.error(f"Search failed: {e}")
                        return []
                    await asyncio.sleep(1)
        return []

    async def _perform_extract(self, urls: List[str], objective: str = "") -> List[Dict[str, Any]]:
        """Internal batch extract helper with fixed constants"""
        async with self._extract_semaphore:
            for attempt in range(self.max_retries):
                try:
                    headers = {
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "parallel-beta": "search-extract-2025-10-10"
                    }
                    
                    # Hardcoded constants
                    payload = {
                        "urls": urls[:10],
                        "excerpts": True, 
                        "full_content": False 
                    }
                    
                    # Use query as objective to guide extraction, but don't expose it as a tunable kwarg
                    if objective:
                        payload["objective"] = objective
                        
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        response = await client.post(self.extract_url, json=payload, headers=headers)
                        
                        if response.status_code == 429:
                             wait_time = 2 ** (attempt + 1)
                             await asyncio.sleep(wait_time)
                             continue

                        if response.status_code != 200:
                            if hasattr(self, 'logger') and self.logger:
                                self.logger.warning(f"Extract API Error {response.status_code}: {response.text}")
                            return []
                            
                        data = response.json()
                        results = []
                        for item in data.get("results", []):
                            content = item.get("full_content", "")
                            if not content:
                                excerpts = item.get("excerpts", [])
                                parts = []
                                for e in excerpts:
                                    if isinstance(e, str): parts.append(e)
                                    elif isinstance(e, dict): parts.append(e.get("text", ""))
                                content = "\n\n".join(parts)
                                
                            results.append({
                                "url": item.get("url", ""),
                                "content": content
                            })
                        return results
                        
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        if hasattr(self, 'logger') and self.logger:
                             self.logger.error(f"Extract failed: {e}")
                        return []
                    await asyncio.sleep(1)
        return []
