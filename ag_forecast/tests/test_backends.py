import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel
from ag_forecast.src.backends.openai_backend import OpenAIBackend
from ag_forecast.src.backends.anthropic_backend import AnthropicBackend

class SampleModel(BaseModel):
    reasoning: str
    answer: str

@pytest.mark.asyncio
async def test_openai_backend_generate():
    with patch("src.backends.openai_backend.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        backend = OpenAIBackend(api_key="test")
        response = await backend.generate([{"role": "user", "content": "Hello"}])
        assert response == "Test response"

@pytest.mark.asyncio
async def test_openai_backend_structured():
    with patch("src.backends.openai_backend.AsyncOpenAI") as MockClient:
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        expected_obj = SampleModel(reasoning="Because", answer="42")
        mock_response.choices[0].message.parsed = expected_obj
        mock_instance.beta.chat.completions.parse = AsyncMock(return_value=mock_response)

        backend = OpenAIBackend(api_key="test")
        response = await backend.generate_structured([{"role": "user", "content": "Solve"}], SampleModel)
        assert response == expected_obj

@pytest.mark.asyncio
async def test_anthropic_backend_generate():
    with patch("src.backends.anthropic_backend.AsyncAnthropic") as MockClient:
        mock_instance = MockClient.return_value
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Claude response")]
        mock_instance.messages.create = AsyncMock(return_value=mock_response)

        backend = AnthropicBackend(api_key="test")
        response = await backend.generate([{"role": "user", "content": "Hello"}])
        assert response == "Claude response"
