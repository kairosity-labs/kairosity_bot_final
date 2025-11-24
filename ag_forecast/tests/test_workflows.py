import pytest
from unittest.mock import AsyncMock, MagicMock
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval, RetrievalStep, SearchQuery
from ag_forecast.src.workflows.researcher_agent import ResearcherAgent, ResearchOutput

@pytest.mark.asyncio
async def test_agentic_retrieval():
    mock_backend = MagicMock()
    mock_backend.generate_structured = AsyncMock()
    mock_backend.generate = AsyncMock(return_value="Final Summary")
    
    # Mock plan: 1st round search, 2nd round sufficient
    step1 = RetrievalStep(
        reasoning="Need info", 
        search_queries=[SearchQuery(query="test", rationale="r", source="mock")], 
        is_sufficient=False
    )
    step2 = RetrievalStep(
        reasoning="Done", 
        search_queries=[], 
        is_sufficient=True
    )
    mock_backend.generate_structured.side_effect = [step1, step2]
    
    mock_mcp = MagicMock()
    mock_mcp.search = AsyncMock(return_value=[{"content": "result"}])
    
    workflow = AgenticRetrieval(mock_backend, {"mock": mock_mcp})
    result = await workflow.run("query")
    
    assert result["summary"] == "Final Summary"
    assert len(result["retrieved_data"]) == 1
    assert result["rounds_used"] == 2

@pytest.mark.asyncio
async def test_researcher_agent_success():
    mock_backend = MagicMock()
    
    valid_code = "def predict(): return {'yes': 0.7, 'no': 0.3}"
    output = ResearchOutput(
        analysis="Analysis", 
        sources_used=[], 
        math_model_description="Desc", 
        python_code=valid_code
    )
    mock_backend.generate_structured = AsyncMock(return_value=output)
    
    agent = ResearcherAgent(mock_backend)
    result = await agent.run("q", "ctx")
    
    assert result["prediction"]["yes"] == 0.7

@pytest.mark.asyncio
async def test_researcher_agent_retry():
    mock_backend = MagicMock()
    
    bad_code = "def predict(): return 'not a dict'"
    good_code = "def predict(): return {'yes': 0.8}"
    
    output_bad = ResearchOutput(analysis="Bad", sources_used=[], math_model_description="", python_code=bad_code)
    output_good = ResearchOutput(analysis="Good", sources_used=[], math_model_description="", python_code=good_code)
    
    mock_backend.generate_structured = AsyncMock(side_effect=[output_bad, output_good])
    
    agent = ResearcherAgent(mock_backend)
    result = await agent.run("q", "ctx")
    
    assert result["prediction"]["yes"] == 0.8
    assert result["attempt"] == 2
