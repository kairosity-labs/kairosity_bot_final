import os
from typing import Optional
from .openai_backend import OpenAIBackend

class OpenRouterBackend(OpenAIBackend):
    def __init__(self, model_name: str = "openai/gpt-4o", api_key: Optional[str] = None, **kwargs):
        # OpenRouter uses the OpenAI client but with a different base URL
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        super().__init__(model_name, api_key, base_url="https://openrouter.ai/api/v1", **kwargs)
