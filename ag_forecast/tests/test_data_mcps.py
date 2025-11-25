import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ag_forecast.src.data_mcps.perplexity_mcp import PerplexityMCP
from ag_forecast.src.data_mcps.asknews_mcp import AskNewsMCP
from ag_forecast.src.data_mcps.duckduckgo_mcp import DuckDuckGoMCP


@pytest.mark.asyncio
async def test_perplexity_search() -> None:
    with patch("ag_forecast.src.data_mcps.perplexity_mcp.httpx.AsyncClient") as MockClient:
        mock_instance = MockClient.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Perplexity answer"}}],
            "citations": ["http://example.com"],
        }
        mock_instance.post = AsyncMock(return_value=mock_response)

        mcp = PerplexityMCP(api_key="test")
        results = await mcp.search("query")
        assert len(results) == 1
        assert results[0]["content"] == "Perplexity answer"
        assert results[0]["citations"] == ["http://example.com"]


@pytest.mark.asyncio
async def test_asknews_search() -> None:
    with patch("ag_forecast.src.data_mcps.asknews_mcp.AskNewsSearcher") as MockSearcher:
        mock_instance = MockSearcher.return_value
        mock_instance.get_formatted_news_async = AsyncMock(return_value="Formatted news")

        mcp = AskNewsMCP()
        results = await mcp.search("query")
        assert len(results) == 1
        assert results[0]["content"] == "Formatted news"
        assert results[0]["source"] == "asknews"


@pytest.mark.asyncio
async def test_duckduckgo_search() -> None:
    with patch("ag_forecast.src.data_mcps.duckduckgo_mcp.DDGS") as MockDDGS:
        mock_ddgs_instance = MockDDGS.return_value.__enter__.return_value
        mock_ddgs_instance.text.return_value = [
            {"title": "DDG Result", "body": "Content", "href": "url"}
        ]

        mcp = DuckDuckGoMCP()
        results = await mcp.search("query")
        assert len(results) == 1
        assert results[0]["title"] == "DDG Result"
