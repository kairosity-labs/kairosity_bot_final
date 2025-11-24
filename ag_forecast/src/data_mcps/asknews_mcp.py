import os
import httpx
from typing import List, Dict, Any
from .base import BaseDataMCP

class AskNewsMCP(BaseDataMCP):
    def __init__(self, api_key: str = None, **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = self.api_key or os.getenv("ASKNEWS_API_KEY")
        self.base_url = "https://api.asknews.app/v1/news/search"

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        params = {
            "q": query,
            "n_articles": kwargs.get("limit", 5),
            "return_type": "json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for article in data.get("articles", []):
                results.append({
                    "title": article.get("title"),
                    "content": article.get("summary"),
                    "url": article.get("article_url"),
                    "source": "asknews",
                    "published_at": article.get("pub_date")
                })
            return results
