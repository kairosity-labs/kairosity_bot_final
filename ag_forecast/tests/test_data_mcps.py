import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ag_forecast.src.data_mcps.perplexity_mcp import PerplexityMCP
from ag_forecast.src.data_mcps.asknews_mcp import AskNewsMCP
from ag_forecast.src.data_mcps.duckduckgo_mcp import DuckDuckGoMCP

@pytest.mark.asyncio
async def test_perplexity_search():
    with patch("src.data_mcps.perplexity_mcp.httpx.AsyncClient") as MockClient:
        mock_instance = MockClient.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Perplexity answer"}}],
            "citations": ["http://example.com"]
        }
        mock_instance.post = AsyncMock(return_value=mock_response)

        mcp = PerplexityMCP(api_key="test")
        results = await mcp.search("query")
        assert len(results) == 1
        assert results[0]["content"] == "Perplexity answer"
        assert results[0]["citations"] == ["http://example.com"]

@pytest.mark.asyncio
async def test_asknews_search():
    with patch("src.data_mcps.asknews_mcp.httpx.AsyncClient") as MockClient:
        mock_instance = MockClient.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {"title": "News 1", "summary": "Summary 1", "article_url": "url1", "pub_date": "2023"}
            ]
        }
        mock_instance.get = AsyncMock(return_value=mock_response)

        mcp = AskNewsMCP(api_key="test")
        results = await mcp.search("query")
        assert len(results) == 1
        assert results[0]["title"] == "News 1"

@pytest.mark.asyncio
async def test_duckduckgo_search():
    # Mocking the internal DDGS class or the run_in_executor
    with patch("src.data_mcps.duckduckgo_mcp.DDGS") as MockDDGS:
        mock_ddgs_instance = MockDDGS.return_value.__enter__.return_value
        mock_ddgs_instance.text.return_value = [
            {"title": "DDG Result", "body": "Content", "href": "url"}
        ]
        
        mcp = DuckDuckGoMCP()
        results = await mcp.search("query")
        assert len(results) == 1
        assert results[0]["title"] == "DDG Result"
