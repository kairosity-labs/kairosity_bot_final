import pytest
from unittest.mock import AsyncMock, MagicMock
from ag_forecast.src.community.community import Community

@pytest.mark.asyncio
async def test_community_run():
    agent1 = MagicMock()
    agent1.run = AsyncMock(return_value={"prediction": {"yes": 0.6}})
    
    agent2 = MagicMock()
    agent2.run = AsyncMock(return_value={"prediction": {"yes": 0.8}})
    
    community = Community([agent1, agent2])
    results = await community.run("q", "ctx")
    
    assert len(results) == 2
    assert results[0]["prediction"]["yes"] == 0.6
    assert results[1]["prediction"]["yes"] == 0.8
