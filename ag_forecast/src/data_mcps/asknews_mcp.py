from typing import Any

from forecasting_tools.helpers.asknews_searcher import AskNewsSearcher

from .base import BaseDataMCP


class AskNewsMCP(BaseDataMCP):
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, **kwargs: Any) -> None:
        super().__init__(None, **kwargs)
        self.searcher = AskNewsSearcher(client_id=client_id, client_secret=client_secret)

    async def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        formatted_news = await self.searcher.get_formatted_news_async(query)
        return [
            {
                "content": formatted_news,
                "source": "asknews",
            }
        ]
