import asyncio
import traceback
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.prompts import (
    RESEARCHER_AGENT_SYSTEM_PROMPT,
    RESEARCHER_AGENT_USER_PROMPT,
    RESEARCHER_AGENT_ERROR_PROMPT
)

class FollowUpQuery(BaseModel):
    query: str
    type: str  # "short-form" or "long-form"
    rationale: str

class ResearchOutput(BaseModel):
    analysis: str
    sources_used: List[str]
    followup_queries: List[FollowUpQuery]  # 5 queries the researcher would like to look up
    math_model_description: str
    python_code: str  # The code must define a function `predict() -> Dict[str, float]`

class ResearcherAgent:
    def __init__(self, backend: BaseBackend, max_retries: int = 3, logger=None, agent_id: int = 0):
        self.backend = backend
        self.max_retries = max_retries
        self.logger = logger
        self.agent_id = agent_id

    async def run(self, question: str, context: str, current_date: str = None, prediction_schema: Dict[str, Any] = None) -> Dict[str, Any]:
        from datetime import datetime
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.researcher(self.agent_id, "Starting analysis")
        
        # Format prompt with schema if provided
        system_prompt = RESEARCHER_AGENT_SYSTEM_PROMPT.format(current_date=current_date)
        if prediction_schema:
            schema_instruction = (
                f"\n\nIMPORTANT: You must use the following prediction schema:\n"
                f"Type: {prediction_schema.get('schema_type')}\n"
                f"Options (Keys): {prediction_schema.get('options')}\n"
                f"Description: {prediction_schema.get('description')}\n"
                f"Your `predict()` function MUST return a dictionary with EXACTLY these keys."
            )
            system_prompt += schema_instruction
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": RESEARCHER_AGENT_USER_PROMPT.format(question=question, context=context)}
        ]

        for attempt in range(self.max_retries):
            try:
                if self.logger:
                    self.logger.researcher(self.agent_id, f"Attempt {attempt + 1}/{self.max_retries}")
                
                # 1. Generate Analysis and Code
                output = await self.backend.generate_structured(messages, ResearchOutput)
                
                if self.logger:
                    self.logger.researcher(self.agent_id, f"Analysis: {output.analysis[:200]}...")
                    self.logger.researcher(self.agent_id, f"Model: {output.math_model_description[:200]}...")
                
                # 2. Verify Code
                local_scope = {}
                exec(output.python_code, {}, local_scope)
                
                if "predict" not in local_scope:
                    raise ValueError("Function `predict` not found in generated code.")
                
                prediction = local_scope["predict"]()
                
                if not isinstance(prediction, dict):
                    raise ValueError("`predict` function must return a dictionary.")
                
                if self.logger:
                    self.logger.researcher(self.agent_id, f"Prediction: {prediction}")
                    self.logger.researcher(self.agent_id, f"Follow-up queries: {len(output.followup_queries)}")
                    self.logger.researcher(self.agent_id, "✓ Code verified successfully")
                    # Save code and prediction with follow-up queries
                    self.logger.save_researcher_code(
                        self.agent_id, 
                        output.python_code, 
                        prediction, 
                        output.analysis,
                        [q.dict() for q in output.followup_queries]
                    )
                    self.logger.log_event(f"ResearcherAgent_{self.agent_id}", "prediction",
                                          input_data={"question": question, "schema": prediction_schema},
                                          output_data={
                                              "prediction": prediction,
                                              "analysis": output.analysis,
                                              "code": output.python_code,
                                              "followup_queries": [q.dict() for q in output.followup_queries]
                                          })
                
                # If successful, return
                return {
                    "analysis": output.analysis,
                    "model_desc": output.math_model_description,
                    "code": output.python_code,
                    "prediction": prediction,
                    "followup_queries": [q.dict() for q in output.followup_queries],
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                error_msg = f"Error in attempt {attempt+1}: {str(e)}\n{traceback.format_exc()}"
                if self.logger:
                    self.logger.researcher(self.agent_id, f"✗ Verification failed: {str(e)}")
                messages.append({"role": "user", "content": RESEARCHER_AGENT_ERROR_PROMPT.format(error_msg=error_msg)})
        
        if self.logger:
            self.logger.researcher(self.agent_id, "✗ Max retries reached - FAILED")
        raise RuntimeError("Max retries reached for ResearcherAgent.")
