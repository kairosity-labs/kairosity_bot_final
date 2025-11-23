import os
import httpx
from typing import List, Dict, Any
from .base import BaseDataMCP

class PerplexityMCP(BaseDataMCP):
    def __init__(self, api_key: str = None, model: str = "llama-3.1-sonar-small-128k-online", **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = self.api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        self.base_url = "https://api.perplexity.ai/chat/completions"

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Perplexity 'search' is essentially a chat completion with internet access.
        We'll return the content as a single 'result' item, or parse citations if available.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Be precise and concise."},
                {"role": "user", "content": query}
            ],
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])
            
            # Return as a structured result
            return [{
                "content": content,
                "citations": citations,
                "source": "perplexity"
            }]
