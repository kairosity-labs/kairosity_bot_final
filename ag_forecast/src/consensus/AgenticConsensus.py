"""
AgenticConsensus - LLM-powered intelligent consensus mechanism for researcher predictions.

This module provides an intelligent alternative to statistical consensus methods,
using an LLM to evaluate researcher analysis quality, model soundness, and prediction
validity before computing a weighted consensus.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from ag_forecast.src.consensus.base import BaseConsensus
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.prompts import (
    AGENTIC_CONSENSUS_SYSTEM_PROMPT,
    AGENTIC_CONSENSUS_USER_PROMPT
)


class ResearcherEvaluation(BaseModel):
    """Evaluation of a single researcher's output by the Consensus Agent."""
    researcher_id: Optional[int] = Field(default=None, description="Index of the researcher (0-based)")
    analysis_quality: Optional[float] = Field(default=None, description="Quality score for the analysis (0-1)")
    model_soundness: Optional[float] = Field(default=None, description="Soundness score for the mathematical model (0-1)")
    normalized_prediction: Optional[Dict[str, float]] = Field(default=None, description="Unit-corrected prediction values")
    weight: Optional[float] = Field(default=None, description="Weight assigned to this researcher's prediction (0-1)")
    reasoning: Optional[str] = Field(default=None, description="Explanation for the evaluation and weight assignment")
    should_include: Optional[bool] = Field(default=None, description="Whether to include this prediction in the consensus")


class ConsensusOutput(BaseModel):
    """Structured output from the Consensus Agent's LLM evaluation."""
    evaluations: Optional[List[ResearcherEvaluation]] = Field(default=None, description="Evaluations for each researcher")
    consensus_reasoning: Optional[str] = Field(default=None, description="Overall reasoning for the consensus decision")


class AgenticConsensus(BaseConsensus):
    """
    LLM-powered consensus mechanism that intelligently weights researcher predictions.
    
    Unlike statistical methods (mean, median, weighted average), AgenticConsensus:
    - Evaluates the quality of each researcher's analysis
    - Validates the soundness of their mathematical models
    - Normalizes predictions (handles unit mismatches)
    - Assigns weights based on reasoning quality
    - Can reject fundamentally flawed predictions
    
    Usage:
        consensus = AgenticConsensus(backend=my_llm_backend)
        result = await consensus.aggregate_async(
            researcher_outputs=community_results,
            question="Will X happen by 2025?",
            prediction_schema={"yes": float, "no": float},
            current_date="2024-12-14"
        )
    """
    
    def __init__(self, backend: BaseBackend, max_tokens: int = 16384, logger=None):
        self.max_tokens = max_tokens
        self.backend = backend
        self.logger = logger
    
    def aggregate(self, predictions: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Synchronous fallback that computes simple mean.
        
        For full LLM-powered evaluation, use aggregate_async() with complete
        researcher outputs including analysis, model_desc, and predictions.
        
        Args:
            predictions: List of prediction dictionaries
            
        Returns:
            Mean consensus prediction
        """
        if not predictions:
            return {}
        
        keys = predictions[0].keys()
        result = {}
        for k in keys:
            values = [p.get(k, 0.0) for p in predictions]
            result[k] = sum(values) / len(values)
        return result
    
    async def aggregate_async(
        self,
        researcher_outputs: List[Dict[str, Any]],
        question: str,
        prediction_schema: Dict[str, Any],
        current_date: str = None,
        parent_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Async method that uses LLM to evaluate and weight predictions.
        
        Args:
            researcher_outputs: List of dicts from ResearcherAgent.run(), each containing:
                - analysis: str - The researcher's analysis text
                - model_desc: str - Description of the mathematical model
                - code: str - Python code for the model
                - prediction: Dict[str, float] - The prediction output
            question: The forecasting question being answered
            prediction_schema: Schema for the prediction format
            current_date: Current date for context
            
        Returns:
            Dict containing:
                - prediction: Dict[str, float] - The weighted consensus prediction
                - evaluations: List[ResearcherEvaluation] - Individual evaluations
                - reasoning: str - Overall consensus reasoning
        """
        from datetime import datetime
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.info(f"[AgenticConsensus] Evaluating {len(researcher_outputs)} researcher predictions")
        
        # Format researcher outputs for the prompt
        formatted_outputs = self._format_researcher_outputs(researcher_outputs)
        
        # Build messages for LLM
        system_prompt = AGENTIC_CONSENSUS_SYSTEM_PROMPT.format(current_date=current_date)
        user_prompt = AGENTIC_CONSENSUS_USER_PROMPT.format(
            question=question,
            prediction_schema=self._format_schema(prediction_schema),
            researcher_outputs_formatted=formatted_outputs
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Get structured evaluation from LLM
        consensus_output = await self.backend.generate_structured(messages, ConsensusOutput, max_tokens=self.max_tokens)
        
        # Safety: ensure evaluations is not None
        if consensus_output.evaluations is None:
            if self.logger:
                self.logger.warning("[AgenticConsensus] LLM returned None evaluations, using empty list")
            consensus_output.evaluations = []
        
        if self.logger:
            self.logger.subsection("CONSENSUS EVALUATION")
            for eval in consensus_output.evaluations:
                status = "✓ INCLUDED" if eval.should_include else "✗ EXCLUDED"
                researcher_num = eval.researcher_id + 1 if eval.researcher_id is not None else "?"
                # Safely format optional float values
                weight_str = f"{eval.weight:.2f}" if eval.weight is not None else "N/A"
                analysis_str = f"{eval.analysis_quality:.2f}" if eval.analysis_quality is not None else "N/A"
                model_str = f"{eval.model_soundness:.2f}" if eval.model_soundness is not None else "N/A"
                self.logger.info(
                    f"[AgenticConsensus] Researcher #{researcher_num}: "
                    f"weight={weight_str}, analysis={analysis_str}, "
                    f"model={model_str} → {status}"
                )
        
        # Compute weighted consensus from evaluations
        weighted_prediction = self._compute_weighted_consensus(consensus_output.evaluations)
        
        if self.logger:
            self.logger.info(f"[AgenticConsensus] Final weighted prediction: {weighted_prediction}")
            
            # Log consensus event to observability graph
            consensus_node_id = self.logger.log_event(
                "AgenticConsensus",
                "weighted_consensus",
                input_data={
                    "question": question,
                    "num_researchers": len(researcher_outputs),
                    "schema": prediction_schema
                },
                output_data={
                    "consensus_prediction": weighted_prediction,
                    "consensus_reasoning": consensus_output.consensus_reasoning,
                    "evaluations": [e.model_dump() for e in consensus_output.evaluations]
                },
                parent_ids=parent_ids
            )
        else:
            consensus_node_id = None
        
        return {
            "prediction": weighted_prediction,
            "evaluations": [e.model_dump() for e in consensus_output.evaluations],
            "reasoning": consensus_output.consensus_reasoning,
            "last_node_id": consensus_node_id
        }
    
    def _format_researcher_outputs(self, researcher_outputs: List[Dict[str, Any]]) -> str:
        """Format researcher outputs for the user prompt."""
        formatted = []
        for i, output in enumerate(researcher_outputs):
            section = f"""
### RESEARCHER #{i}

**Analysis:**
{output.get('analysis', 'N/A')}

**Mathematical Model Description:**
{output.get('model_desc', 'N/A')}

**Prediction:**
{output.get('prediction', {})}
"""
            formatted.append(section)
        return "\n---\n".join(formatted)
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format prediction schema for display."""
        if isinstance(schema, str):
            return schema
        if isinstance(schema, dict):
            if 'schema_type' in schema:
                return f"Type: {schema.get('schema_type')}, Options: {schema.get('options')}"
            return str(schema)
        return str(schema)
    
    def _compute_weighted_consensus(
        self,
        evaluations: List[ResearcherEvaluation]
    ) -> Dict[str, float]:
        """
        Compute weighted sum of predictions based on LLM-assigned weights.
        
        Args:
            evaluations: List of ResearcherEvaluation from LLM
            
        Returns:
            Dict[str, float] weighted consensus prediction
        """
        # Filter to included predictions only  (handle None values)
        included = [e for e in evaluations if e.should_include is True and e.normalized_prediction is not None]
        
        if not included:
            if self.logger:
                self.logger.warning("[AgenticConsensus] All predictions rejected, falling back to mean")
            # Fallback: use all predictions with equal weight
            included = [e for e in evaluations if e.normalized_prediction is not None]
            if not included:
                raise ValueError("No valid predictions with normalized_prediction available")
            for e in included:
                e.weight = 1.0 / len(included)
        
        # Normalize weights to sum to 1 (handle None weights)
        total_weight = sum(e.weight if e.weight is not None else 0.0 for e in included)
        if total_weight == 0:
            total_weight = 1.0
            for e in included:
                e.weight = 1.0 / len(included)
        
        # Get all keys from the first prediction (safe since we checked normalized_prediction is not None)
        keys = included[0].normalized_prediction.keys()
        
        # Compute weighted sum for each key
        result = {}
        for key in keys:
            weighted_sum = sum(
                e.normalized_prediction.get(key, 0.0) * ((e.weight if e.weight is not None else 0.0) / total_weight)
                for e in included
            )
            result[key] = weighted_sum
        
        return result
