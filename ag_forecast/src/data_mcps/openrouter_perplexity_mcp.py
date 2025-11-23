import os
import httpx
from typing import List, Dict, Any
from .base import BaseDataMCP
from ag_forecast.src.prompts import PERPLEXITY_SYSTEM_PROMPT

class OpenRouterPerplexityMCP(BaseDataMCP):
    def __init__(self, api_key: str = None, model: str = "perplexity/llama-3.1-sonar-large-128k-online", **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = self.api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Uses OpenRouter to access Perplexity online models.
        """
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/metaculus-bot",
            "X-Title": "Metaculus Bot"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": PERPLEXITY_SYSTEM_PROMPT.format(current_date=current_date)},
                {"role": "user", "content": query}
            ],
            **kwargs
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            if response.status_code != 200:
                error_msg = f"OpenRouter Error {response.status_code}: {response.text}"
                raise Exception(error_msg)
            
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            
            # OpenRouter might not pass citations in the same way as direct Perplexity API.
            # We'll check if they exist in the response, otherwise just return content.
            citations = data.get("citations", [])
            
            return [{
                "content": content,
                "citations": citations,
                "source": "perplexity_openrouter"
            }]
