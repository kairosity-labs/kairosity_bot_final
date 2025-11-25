import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.prompts import (
    SUPERVISOR_AGENT_SYSTEM_PROMPT,
    SUPERVISOR_AGENT_USER_PROMPT
)

class SubQuery(BaseModel):
    query: str
    rationale: str

class SupervisorOutput(BaseModel):
    critique: str
    is_sufficient: bool
    sub_queries: List[SubQuery]

class SupervisorAgent:
    def __init__(self, backend: BaseBackend, logger=None):
        self.backend = backend
        self.logger = logger

    async def run(self, user_query: str, global_context: str, current_date: str = None, parent_ids: List[str] = None) -> Dict[str, Any]:
        from datetime import datetime
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.subsection("SUPERVISOR REVIEW")
        
        messages = [
            {"role": "system", "content": SUPERVISOR_AGENT_SYSTEM_PROMPT.format(
                current_date=current_date,
                user_query=user_query
            )},
            {"role": "user", "content": SUPERVISOR_AGENT_USER_PROMPT.format(context=global_context)}
        ]

        # Generate Critique and Plan
        output = await self.backend.generate_structured(messages, SupervisorOutput)
        
        if self.logger:
            self.logger.info(f"Critique: {output.critique}")
            self.logger.info(f"Is sufficient: {output.is_sufficient}")
            self.logger.info(f"Is sufficient: {output.is_sufficient}")
            review_node_id = self.logger.log_event("SupervisorAgent", "review",
                                  input_data={"global_context_length": len(global_context)},
                                  output_data=output.dict(),
                                  parent_ids=parent_ids)
            if not output.is_sufficient:
                self.logger.info(f"Generated {len(output.sub_queries)} new sub-queries")
                for q in output.sub_queries:
                    self.logger.info(f"  - {q.query} ({q.rationale})")
        
        return {
            "critique": output.critique,
            "is_sufficient": output.is_sufficient,
            "sub_queries": [q.dict() for q in output.sub_queries],
            "last_node_id": review_node_id if self.logger else None
        }
