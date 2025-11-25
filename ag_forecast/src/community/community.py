import asyncio
from typing import List, Dict, Any
from ag_forecast.src.workflows.researcher_agent import ResearcherAgent

class Community:
    def __init__(self, agents: List[ResearcherAgent], logger=None):
        self.agents = agents
        self.logger = logger

    async def run(self, question: str, context: str, current_date: str = None, prediction_schema: Dict[str, Any] = None, parent_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Run all agents in parallel.
        """
        if self.logger:
            self.logger.subsection("COMMUNITY OF RESEARCHERS")
            self.logger.info(f"Running {len(self.agents)} researchers in parallel")
        
        tasks = [agent.run(question, context, current_date, prediction_schema, parent_ids) for agent in self.agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, res in enumerate(results):
            if isinstance(res, dict):
                valid_results.append(res)
                if self.logger:
                    self.logger.info(f"Researcher #{i+1}: SUCCESS - Prediction: {res.get('prediction', {})}")
            else:
                if self.logger:
                    self.logger.error(f"Researcher #{i+1}: FAILED - {str(res)}")
                
        if self.logger:
            self.logger.info(f"\nSuccessful researchers: {len(valid_results)}/{len(self.agents)}")
        
        return valid_results
