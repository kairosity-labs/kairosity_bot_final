import os
from typing import List, Dict, Any, Union, Optional
from pydantic import BaseModel
from openai import AsyncOpenAI
from .base import BaseBackend

class OpenAIBackend(BaseBackend):
    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        client_kwargs = {"api_key": self.api_key or os.getenv("OPENAI_API_KEY")}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**client_kwargs)

    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # Set default max_tokens if not provided to prevent truncation
        if 'max_tokens' not in kwargs:
            kwargs['max_tokens'] = 4096
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content

    async def generate_structured(self, messages: List[Dict[str, str]], response_model: type[BaseModel], **kwargs) -> BaseModel:
        # Set default max_tokens if not provided to prevent JSON truncation
        if 'max_tokens' not in kwargs:
            kwargs['max_tokens'] = 4096
        response = await self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            response_format=response_model,
            **kwargs
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            # Check if there was a refusal
            refusal = response.choices[0].message.refusal
            if refusal:
                raise ValueError(f"Model refused to respond: {refusal}")
            raise ValueError(f"Failed to parse response into {response_model.__name__}. Raw content: {response.choices[0].message.content}")
        return parsed

    async def tool_call(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Union[str, Dict[str, Any]]:
        # Set default max_tokens if not provided
        if 'max_tokens' not in kwargs:
            kwargs['max_tokens'] = 4096
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            **kwargs
        )
        message = response.choices[0].message
        if message.tool_calls:
            return {
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        },
                        "type": tc.type
                    } for tc in message.tool_calls
                ]
            }
        return message.content
