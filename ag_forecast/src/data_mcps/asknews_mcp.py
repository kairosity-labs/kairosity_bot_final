import asyncio
from typing import Any

from forecasting_tools.helpers.asknews_searcher import AskNewsSearcher

from .base import BaseDataMCP


class AskNewsMCP(BaseDataMCP):
    # Class-level semaphore to limit concurrent requests to AskNews API
    # Set to 1 to prevent "Concurrency Limit Exceeded" errors
    _semaphore = asyncio.Semaphore(1)
    
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, max_retries: int = 3, **kwargs: Any) -> None:
        super().__init__(None, **kwargs)
        self.searcher = AskNewsSearcher(client_id=client_id, client_secret=client_secret)
        self.max_retries = max_retries

    async def search(self, query: str) -> list[dict[str, Any]]:
        # Hardcoded defaults: kw method, both return type, last 48 hours, 10 results
        if not query:
            return []
        
        # Use semaphore to ensure only one request at a time
        async with self._semaphore:
            # Retry with exponential backoff for rate limit errors
            for attempt in range(self.max_retries):
                try:
                    formatted_news = await self.searcher.get_formatted_news_async(query)
                    return [
                        {
                            "content": formatted_news,
                            "source": "asknews",
                        }
                    ]
                except Exception as e:
                    error_str = str(e)
                    # Check if it's a rate limit error
                    if "429000" in error_str or "Rate Limit Exceeded" in error_str:
                        if attempt < self.max_retries - 1:
                            # Exponential backoff: 2, 4, 8 seconds
                            wait_time = 2 ** (attempt + 1)
                            print(f"AskNews rate limit hit. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                    # Re-raise if it's not a rate limit error or we're out of retries
                    raise
            
            # If we get here, all retries failed
            raise Exception(f"AskNews search failed after {self.max_retries} retries")
