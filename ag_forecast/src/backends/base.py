from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

class BaseBackend(ABC):
    """Abstract base class for LLM backends."""

    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs):
        self.model_name = model_name
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts (role, content).
            **kwargs: Additional generation parameters (temperature, max_tokens, etc.).
            
        Returns:
            The generated text response.
        """
        pass

    @abstractmethod
    async def generate_structured(self, messages: List[Dict[str, str]], response_model: type[BaseModel], **kwargs) -> BaseModel:
        """
        Generate a structured response matching a Pydantic model.
        
        Args:
            messages: List of message dicts.
            response_model: The Pydantic model class to enforce structure.
            **kwargs: Additional parameters.
            
        Returns:
            An instance of response_model.
        """
        pass
    
    @abstractmethod
    async def tool_call(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Union[str, Dict[str, Any]]:
        """
        Generate a response that may include tool calls.
        
        Args:
            messages: List of message dicts.
            tools: List of tool definitions (JSON schema).
            **kwargs: Additional parameters.
            
        Returns:
            Either a text response or a tool call dictionary.
        """
        pass
