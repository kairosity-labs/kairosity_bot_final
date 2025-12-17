import os
import asyncio
import httpx
from typing import List, Dict, Any
from .base import BaseDataMCP


class PerplexitySonarMCP(BaseDataMCP):
    """
    Perplexity Sonar MCP - AI-synthesized answers with citations.
    
    Uses chat completions API with 'sonar' model for cost-effective grounded responses.
    Best for: Quick answers, summaries, synthesized insights.
    """
    # Semaphore - lazily initialized to avoid event loop issues with nest_asyncio
    _semaphore_instance = None
    
    @property
    def _semaphore(self):
        if PerplexitySonarMCP._semaphore_instance is None:
            PerplexitySonarMCP._semaphore_instance = asyncio.Semaphore(3)
        return PerplexitySonarMCP._semaphore_instance
    
    def __init__(self, api_key: str = None, model: str = "sonar", max_retries: int = 3, **kwargs):
        super().__init__(api_key, **kwargs)
        self.api_key = self.api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.max_retries = max_retries

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Perplexity Sonar - AI-synthesized answers with citations.
        
        Args:
            query (str): Natural language question
            
        Returns:
            List with single dict containing AI-synthesized content and citations
        """
        if not query:
            return []
            
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Use semaphore to ensure rate limiting
        async with self._semaphore:
            # Retry with exponential backoff for rate limit errors
            for attempt in range(self.max_retries):
                try:
                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    }
                    
                    # Optimal defaults for forecasting research
                    payload = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": f"You are a helpful research assistant. Be precise and concise. Current date: {current_date}"},
                            {"role": "user", "content": query}
                        ],
                        "temperature": 0.2,  # Low temperature for factual accuracy
                        "return_citations": True,  # Always include sources
                        "return_related_questions": True  # Useful for context expansion
                    }
                    
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(self.base_url, json=payload, headers=headers)
                        
                        if response.status_code != 200:
                            error_msg = f"Perplexity API Error {response.status_code}: {response.text}"
                            
                            # Check if it's a rate limit error
                            if response.status_code == 429:
                                if attempt < self.max_retries - 1:
                                    # Exponential backoff: 2, 4, 8 seconds
                                    wait_time = 2 ** (attempt + 1)
                                    print(f"Perplexity rate limit hit. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                                    await asyncio.sleep(wait_time)
                                    continue
                            
                            raise Exception(error_msg)
                        
                        data = response.json()
                        
                        message = data["choices"][0]["message"]
                        content = message["content"]
                        
                        # Extract citations if available
                        citations = []
                        if "citations" in data:
                            citations = data["citations"]
                        elif "citations" in message:
                            citations = message["citations"]
                        
                        return [{
                            "title": "Perplexity Sonar Response",
                            "url": "",
                            "content": content,
                            "citations": citations,
                            "source": "perplexity_sonar"
                        }]
                        
                except Exception as e:
                    # Check if it's a rate limit error from exception message
                    error_str = str(e)
                    if "429" in error_str or "rate limit" in error_str.lower():
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** (attempt + 1)
                            print(f"Perplexity rate limit detected. Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(wait_time)
                            continue
                    # Re-raise if it's not a rate limit error or we're out of retries
                    raise
            
            # If we get here, all retries failed
            raise Exception(f"Perplexity search failed after {self.max_retries} retries")
