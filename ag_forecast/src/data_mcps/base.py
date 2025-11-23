from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseDataMCP(ABC):
    """Abstract base class for Data MCPs (Search APIs)."""

    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Perform a search query.
        
        Args:
            query: The search query string.
            **kwargs: Additional parameters (limit, etc.).
            
        Returns:
            A list of search results (dictionaries).
        """
        pass
