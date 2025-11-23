import asyncio
from typing import Dict, Any, List
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval
from ag_forecast.src.workflows.analyst_agent import AnalystAgent
from ag_forecast.src.workflows.supervisor_agent import SupervisorAgent
from ag_forecast.src.community.community import Community
from ag_forecast.src.consensus.base import BaseConsensus

from ag_forecast.src.workflows.schema_agent import SchemaAgent

class IterativeResearchWorkflow:
    def __init__(self, 
                 retrieval: AgenticRetrieval, 
                 analyst_agent: AnalystAgent,
                 supervisor: SupervisorAgent,
                 schema_agent: SchemaAgent,
                 community: Community, 
                 consensus: BaseConsensus,
                 max_loop_rounds: int = 3,
                 logger=None):
        self.retrieval = retrieval
        self.analyst_agent = analyst_agent
        self.supervisor = supervisor
        self.schema_agent = schema_agent
        self.community = community
        self.consensus = consensus
        self.max_loop_rounds = max_loop_rounds
        self.logger = logger

    async def run(self, user_query: str) -> Dict[str, Any]:
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.section("ITERATIVE RESEARCH WORKFLOW")
            self.logger.info(f"Main Query: {user_query}")
            self.logger.info(f"Max Loop Rounds: {self.max_loop_rounds}")
        
        global_context = []
        
        # --- Initial Phase ---
        if self.logger:
            self.logger.subsection("PHASE 1: INITIAL RESEARCH")
        
        # 1. Initial Retrieval
        retrieval_result = await self.retrieval.run(user_query, current_date)
        initial_context = retrieval_result.get("context_for_researchers", retrieval_result["summary"])
        
        # 2. Initial Analysis
        analysis_result = await self.analyst_agent.run(user_query, initial_context, current_date)
        
        # Add to global context
        global_context.append(f"--- Initial Research ---\nQuery: {user_query}\nAnalysis: {analysis_result['analysis']}")
        
        # --- Iterative Loop ---
        for round_num in range(self.max_loop_rounds):
            if self.logger:
                self.logger.subsection(f"PHASE 2: ITERATIVE LOOP (Round {round_num + 1}/{self.max_loop_rounds})")
            
            # 1. Supervisor Review
            context_str = "\n\n".join(global_context)
            supervisor_result = await self.supervisor.run(user_query, context_str, current_date)
            
            if supervisor_result["is_sufficient"] or not supervisor_result["sub_queries"]:
                if self.logger:
                    self.logger.info("Supervisor determined information is sufficient. Proceeding to forecast.")
                break
            
            # 2. Process Sub-queries
            sub_query_tasks = []
            for sub_q in supervisor_result["sub_queries"]:
                sub_query_tasks.append(self._process_sub_query(sub_q["query"], current_date))
            
            if self.logger:
                self.logger.info(f"Processing {len(sub_query_tasks)} sub-queries in parallel...")
            
            sub_query_results = await asyncio.gather(*sub_query_tasks)
            
            # 3. Update Global Context
            for res in sub_query_results:
                global_context.append(f"--- Sub-query: {res['query']} ---\nAnalysis: {res['analysis']}")
        
        # --- Final Phase ---
        if self.logger:
            self.logger.subsection("PHASE 3: FINAL FORECAST")
        
        final_context_str = "\n\n".join(global_context)
        
        # 1. Define Prediction Schema
        schema_result = await self.schema_agent.run(user_query, final_context_str, current_date)
        
        # 2. Run Community of Researchers (Forecasters)
        community_results = await self.community.run(user_query, final_context_str, current_date, schema_result)
        
        # 2. Aggregate Predictions
        predictions = [res["prediction"] for res in community_results if "prediction" in res]
        aggregated_prediction = self.consensus.aggregate(predictions)
        
        if self.logger:
            self.logger.info(f"\nFinal Aggregated Prediction: {aggregated_prediction}")
            self.logger.save_consensus_data(aggregated_prediction)
            self.logger.log_event("Consensus", "final_forecast",
                                  input_data={"schema": schema_result},
                                  output_data={"prediction": aggregated_prediction})
            self.logger.section("EXECUTION COMPLETE")
            self.logger.info(f"All data saved to: {self.logger.get_run_dir()}")
        
        return {
            "question": user_query,
            "global_context": final_context_str,
            "individual_forecasts": community_results,
            "aggregated_prediction": aggregated_prediction
        }

    async def _process_sub_query(self, query: str, current_date: str) -> Dict[str, Any]:
        """Helper to run retrieval and analysis for a single sub-query."""
        # 1. Retrieve
        retrieval_result = await self.retrieval.run(query, current_date)
        context = retrieval_result.get("context_for_researchers", retrieval_result["summary"])
        
        # 2. Analyze
        analysis_result = await self.analyst_agent.run(query, context, current_date)
        
        return analysis_result

    async def run_research_only(self, user_query: str) -> str:
        """Runs only the research phases (Initial + Iterative) and returns the context."""
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.section("ITERATIVE RESEARCH WORKFLOW (RESEARCH ONLY)")
            self.logger.info(f"Main Query: {user_query}")
            self.logger.info(f"Max Loop Rounds: {self.max_loop_rounds}")
        
        global_context = []
        
        # --- Initial Phase ---
        if self.logger:
            self.logger.subsection("PHASE 1: INITIAL RESEARCH")
        
        # 1. Initial Retrieval
        retrieval_result = await self.retrieval.run(user_query, current_date)
        initial_context = retrieval_result.get("context_for_researchers", retrieval_result["summary"])
        
        # 2. Initial Analysis
        analysis_result = await self.analyst_agent.run(user_query, initial_context, current_date)
        
        # Add to global context
        global_context.append(f"--- Initial Research ---\nQuery: {user_query}\nAnalysis: {analysis_result['analysis']}")
        
        # --- Iterative Loop ---
        for round_num in range(self.max_loop_rounds):
            if self.logger:
                self.logger.subsection(f"PHASE 2: ITERATIVE LOOP (Round {round_num + 1}/{self.max_loop_rounds})")
            
            # 1. Supervisor Review
            context_str = "\n\n".join(global_context)
            supervisor_result = await self.supervisor.run(user_query, context_str, current_date)
            
            if supervisor_result["is_sufficient"] or not supervisor_result["sub_queries"]:
                if self.logger:
                    self.logger.info("Supervisor determined information is sufficient.")
                break
            
            # 2. Process Sub-queries
            sub_query_tasks = []
            for sub_q in supervisor_result["sub_queries"]:
                sub_query_tasks.append(self._process_sub_query(sub_q["query"], current_date))
            
            if self.logger:
                self.logger.info(f"Processing {len(sub_query_tasks)} sub-queries in parallel...")
            
            sub_query_results = await asyncio.gather(*sub_query_tasks)
            
            # 3. Update Global Context
            for res in sub_query_results:
                global_context.append(f"--- Sub-query: {res['query']} ---\nAnalysis: {res['analysis']}")
        
        final_context_str = "\n\n".join(global_context)
        return final_context_str
