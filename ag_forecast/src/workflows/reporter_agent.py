import asyncio
from typing import Dict, Any, List, Optional
from ag_forecast.src.backends.base import BaseBackend


class ReporterAgent:
    def __init__(self, backend: BaseBackend, max_tokens: int = 16384, logger=None):
        self.max_tokens = max_tokens
        self.backend = backend
        self.logger = logger

    async def run(
        self,
        question: str,
        research_context: str,
        researcher_outputs: List[Dict[str, Any]],
        consensus_output: Dict[str, Any],
        supervisor_critique: str,
        current_date: str = None,
        parent_ids: List[str] = None
    ) -> str:
        from datetime import datetime
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.subsection("GENERATING FORECASTING REPORT")
        
        from ag_forecast.src.prompts import (
            REPORTER_AGENT_SYSTEM_PROMPT,
            REPORTER_AGENT_USER_PROMPT
        )
        
        formatted_researchers = self._format_researcher_outputs(researcher_outputs)
        formatted_consensus = self._format_consensus_output(consensus_output)
        
        messages = [
            {
                "role": "system",
                "content": REPORTER_AGENT_SYSTEM_PROMPT.format(current_date=current_date)
            },
            {
                "role": "user",
                "content": REPORTER_AGENT_USER_PROMPT.format(
                    question=question,
                    research_context=research_context,
                    researcher_outputs=formatted_researchers,
                    consensus_output=formatted_consensus,
                    supervisor_critique=supervisor_critique
                )
            }
        ]
        
        report = await self.backend.generate(messages, max_tokens=self.max_tokens)
        
        if self.logger:
            self.logger.info(f"Generated report ({len(report)} characters)")
            self.logger.log_event(
                "ReporterAgent",
                "report_generation",
                input_data={"question": question},
                output_data={"report_length": len(report)},
                parent_ids=parent_ids
            )
        
        return report
    
    def _format_researcher_outputs(self, researcher_outputs: List[Dict[str, Any]]) -> str:
        formatted = []
        for i, output in enumerate(researcher_outputs):
            formatted.append(f"""
### Researcher {i + 1}

**Analysis:**
{output.get('analysis', 'N/A')}

**Mathematical Model:**
{output.get('model_desc', 'N/A')}

**Python Code:**
```python
{output.get('code', 'N/A')}
```

**Prediction:**
{output.get('prediction', 'N/A')}
""")
        return "\n---\n".join(formatted)
    
    def _format_consensus_output(self, consensus_output: Dict[str, Any]) -> str:
        evaluations = consensus_output.get('evaluations', [])
        # Support both key formats from different consensus implementations
        final_prediction = consensus_output.get('consensus_prediction') or consensus_output.get('prediction', {})
        reasoning = consensus_output.get('consensus_reasoning') or consensus_output.get('reasoning', 'N/A')
        
        formatted_evals = []
        for eval_data in evaluations:
            formatted_evals.append(f"""
- **Researcher {eval_data.get('researcher_id', 'N/A')}**
  - Quality Assessment: {eval_data.get('analysis_quality', 'N/A')} (analysis), {eval_data.get('model_soundness', 'N/A')} (model)
  - Weight: {eval_data.get('weight', 'N/A')}
  - Included: {eval_data.get('should_include', 'N/A')}
  - Reasoning: {eval_data.get('reasoning', 'N/A')}
""")
        
        return f"""
**Consensus Reasoning:**
{reasoning}

**Final Consensus Prediction:**
{final_prediction}

**Researcher Evaluations:**
{''.join(formatted_evals)}
"""
