import asyncio
from typing import Dict, Any, List
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval
from ag_forecast.src.community.community import Community
from ag_forecast.src.consensus.base import BaseConsensus

class ForecastingBot:
    def __init__(self, 
                 retrieval: AgenticRetrieval, 
                 community: Community, 
                 consensus: BaseConsensus,
                 logger=None):
        self.retrieval = retrieval
        self.community = community
        self.consensus = consensus
        self.logger = logger

    async def forecast(self, question: str) -> Dict[str, Any]:
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.section("FORECASTING BOT EXECUTION")
            self.logger.info(f"Question: {question}")
        
        # 1. Retrieve Context
        if self.logger:
            self.logger.info("\n[Phase 1/3] Starting retrieval...")
        else:
            print(f"Starting retrieval for: {question}")
        
        retrieval_result = await self.retrieval.run(question, current_date)
        context = retrieval_result.get("context_for_researchers", retrieval_result["summary"])
        
        # 2. Run Community of Researchers
        if self.logger:
            self.logger.info(f"\n[Phase 2/3] Running community of researchers...")
        else:
            print("Running community of researchers...")
        
        community_results = await self.community.run(question, context, current_date)
        
        # 3. Aggregate Predictions
        if self.logger:
            self.logger.subsection("CONSENSUS AGGREGATION")
            self.logger.info(f"Aggregating {len(community_results)} predictions")
        else:
            print("Aggregating predictions...")
        
        predictions = [res["prediction"] for res in community_results if "prediction" in res]
        
        if self.logger:
            for i, pred in enumerate(predictions):
                self.logger.info(f"  Researcher #{i+1}: {pred}")
        
        aggregated_prediction = self.consensus.aggregate(predictions)
        
        if self.logger:
            self.logger.info(f"\nFinal Aggregated Prediction: {aggregated_prediction}")
            # Save consensus data
            self.logger.save_consensus_data(question, predictions, aggregated_prediction)
            self.logger.section("EXECUTION COMPLETE")
            self.logger.info(f"All data saved to: {self.logger.get_run_dir()}")
        
        return {
            "question": question,
            "retrieval_summary": retrieval_result["summary"],
            "individual_forecasts": community_results,
            "aggregated_prediction": aggregated_prediction
        }
