import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.prompts import (
    ANALYST_AGENT_SYSTEM_PROMPT,
    ANALYST_AGENT_USER_PROMPT
)

class AnalystOutput(BaseModel):
    analysis: str
    key_points: List[str]
    missing_information: str

class AnalystAgent:
    def __init__(self, backend: BaseBackend, logger=None, max_tokens: int = 16384):
        self.backend = backend
        self.logger = logger
        self.max_tokens = max_tokens

    async def run(self, query: str, context: str, current_date: str = None, parent_ids: List[str] = None) -> Dict[str, Any]:
        from datetime import datetime
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.info(f"Analyzing sub-query: {query}")
        
        messages = [
            {"role": "system", "content": ANALYST_AGENT_SYSTEM_PROMPT.format(current_date=current_date)},
            {"role": "user", "content": ANALYST_AGENT_USER_PROMPT.format(query=query, context=context)}
        ]

        # Generate Analysis
        output = await self.backend.generate_structured(messages, AnalystOutput, max_tokens=self.max_tokens)
        
        if self.logger:
            self.logger.info(f"Analysis complete. Key points: {len(output.key_points)}")
            analysis_node_id = self.logger.log_event("AnalystAgent", "analysis",
                                  input_data={"query": query},
                                  output_data=output.dict(),
                                  parent_ids=parent_ids)
        
        return {
            "query": query,
            "analysis": output.analysis,
            "key_points": output.key_points,
            "missing_info": output.missing_information,
            "last_node_id": analysis_node_id if self.logger else None
        }
