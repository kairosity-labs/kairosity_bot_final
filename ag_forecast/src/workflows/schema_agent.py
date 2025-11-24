import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.prompts import (
    SCHEMA_AGENT_SYSTEM_PROMPT,
    SCHEMA_AGENT_USER_PROMPT
)

class PredictionSchema(BaseModel):
    schema_type: str  # "binary", "categorical", "numerical_buckets"
    options: List[str]  # The exact keys to be used in the prediction dict
    description: str  # Instructions for researchers on how to use this schema

class SchemaAgent:
    def __init__(self, backend: BaseBackend, logger=None):
        self.backend = backend
        self.logger = logger

    async def run(self, question: str, context: str, current_date: str = None) -> Dict[str, Any]:
        from datetime import datetime
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.subsection("SCHEMA DEFINITION")
        
        messages = [
            {"role": "system", "content": SCHEMA_AGENT_SYSTEM_PROMPT.format(current_date=current_date)},
            {"role": "user", "content": SCHEMA_AGENT_USER_PROMPT.format(question=question, context=context)}
        ]

        # Generate Schema
        output = await self.backend.generate_structured(messages, PredictionSchema)
        
        if self.logger:
            self.logger.info(f"Defined Schema Type: {output.schema_type}")
            self.logger.info(f"Options: {output.options}")
            self.logger.log_event("SchemaAgent", "schema_definition",
                                  input_data={"question": question},
                                  output_data=output.dict())
        
        return {
            "schema_type": output.schema_type,
            "options": output.options,
            "description": output.description
        }
