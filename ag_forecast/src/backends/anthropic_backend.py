import os
import json
from typing import List, Dict, Any, Union, Optional
from pydantic import BaseModel
from anthropic import AsyncAnthropic
from .base import BaseBackend

class AnthropicBackend(BaseBackend):
    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620", api_key: Optional[str] = None, **kwargs):
        super().__init__(model_name, api_key, **kwargs)
        self.client = AsyncAnthropic(api_key=self.api_key or os.getenv("ANTHROPIC_API_KEY"))

    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # Anthropic expects 'system' as a top-level parameter, not in messages list for some versions, 
        # but recent API supports it. We'll separate it for safety if needed, or just pass as is if using latest.
        # For simplicity, assuming standard messages format where system is extracted.
        
        system_prompt = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered_messages.append(msg)
        
        kwargs_call = {"model": self.model_name, "messages": filtered_messages, "max_tokens": 1024}
        if system_prompt:
            kwargs_call["system"] = system_prompt
        kwargs_call.update(kwargs)

        response = await self.client.messages.create(**kwargs_call)
        return response.content[0].text

    async def generate_structured(self, messages: List[Dict[str, str]], response_model: type[BaseModel], **kwargs) -> BaseModel:
        # Anthropic doesn't have a native 'parse' like OpenAI yet, so we use tool use to enforce structure
        tool_schema = {
            "name": "return_structured_output",
            "description": "Return the structured output.",
            "input_schema": response_model.model_json_schema()
        }
        
        tool_choice = {"type": "tool", "name": "return_structured_output"}
        
        # Extract system prompt
        system_prompt = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered_messages.append(msg)

        kwargs_call = {
            "model": self.model_name, 
            "messages": filtered_messages, 
            "max_tokens": 1024,
            "tools": [tool_schema],
            "tool_choice": tool_choice
        }
        if system_prompt:
            kwargs_call["system"] = system_prompt
        kwargs_call.update(kwargs)

        response = await self.client.messages.create(**kwargs_call)
        
        for block in response.content:
            if block.type == "tool_use" and block.name == "return_structured_output":
                return response_model.model_validate(block.input)
        
        raise ValueError("Model did not call the structured output tool.")

    async def tool_call(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], **kwargs) -> Union[str, Dict[str, Any]]:
        # Convert OpenAI-style tools to Anthropic format if necessary, or assume Anthropic format input
        # For this implementation, we'll assume the caller passes Anthropic-compatible tool definitions 
        # or we'd need a converter. Let's assume standard Anthropic input_schema.
        
        system_prompt = None
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered_messages.append(msg)

        kwargs_call = {
            "model": self.model_name, 
            "messages": filtered_messages, 
            "max_tokens": 1024,
            "tools": tools
        }
        if system_prompt:
            kwargs_call["system"] = system_prompt
        kwargs_call.update(kwargs)

        response = await self.client.messages.create(**kwargs_call)
        
        if response.stop_reason == "tool_use":
            tool_calls = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.input) # OpenAI expects string arguments
                        },
                        "type": "function"
                    })
            return {"tool_calls": tool_calls}
            
        return response.content[0].text
