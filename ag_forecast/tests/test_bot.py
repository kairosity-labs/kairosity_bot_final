import pytest
from unittest.mock import AsyncMock, MagicMock
from ag_forecast.src.bot.forecasting_bot import ForecastingBot

@pytest.mark.asyncio
async def test_forecasting_bot_flow():
    # Mock Retrieval
    mock_retrieval = MagicMock()
    mock_retrieval.run = AsyncMock(return_value={"summary": "Context"})
    
    # Mock Community
    mock_community = MagicMock()
    mock_community.run = AsyncMock(return_value=[
        {"prediction": {"yes": 0.6}, "analysis": "A1"},
        {"prediction": {"yes": 0.8}, "analysis": "A2"}
    ])
    
    # Mock Consensus
    mock_consensus = MagicMock()
    mock_consensus.aggregate.return_value = {"yes": 0.7}
    
    bot = ForecastingBot(mock_retrieval, mock_community, mock_consensus)
    result = await bot.forecast("Will it rain?")
    
    assert result["aggregated_prediction"]["yes"] == 0.7
    assert len(result["individual_forecasts"]) == 2
    assert result["retrieval_summary"] == "Context"
