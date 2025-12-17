import asyncio
from typing import Dict, Any, List
from ag_forecast.src.workflows.agentic_retrieval import AgenticRetrieval
from ag_forecast.src.workflows.analyst_agent import AnalystAgent
from ag_forecast.src.workflows.supervisor_agent import SupervisorAgent
from ag_forecast.src.community.community import Community
from ag_forecast.src.consensus.base import BaseConsensus
from ag_forecast.src.consensus.AgenticConsensus import AgenticConsensus

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

    # async def run(self, user_query: str) -> Dict[str, Any]:
    #     from datetime import datetime
    #     current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    #     if self.logger:
    #         self.logger.section("ITERATIVE RESEARCH WORKFLOW")
    #         self.logger.info(f"Main Query: {user_query}")
    #         self.logger.info(f"Max Loop Rounds: {self.max_loop_rounds}")
        
    #     global_context = []
        
    #     # --- Initial Phase ---
    #     if self.logger:
    #         self.logger.subsection("PHASE 1: INITIAL RESEARCH")
        
    #     # 1. Initial Retrieval
    #     retrieval_result = await self.retrieval.run(user_query, current_date, parent_ids=[])
    #     initial_context = retrieval_result.get("context_for_researchers", retrieval_result["summary"])
    #     last_node_ids = [retrieval_result["last_node_id"]] if retrieval_result.get("last_node_id") else []
        
    #     # 2. Initial Analysis
    #     analysis_result = await self.analyst_agent.run(user_query, initial_context, current_date, parent_ids=last_node_ids)
    #     if analysis_result.get("last_node_id"):
    #          last_node_ids = [analysis_result["last_node_id"]]
        
    #     # Add to global context
    #     global_context.append(f"--- Initial Research ---\nQuery: {user_query}\nAnalysis: {analysis_result['analysis']}")
        
    #     # --- Iterative Loop ---
    #     for round_num in range(self.max_loop_rounds):
    #         if self.logger:
    #             self.logger.subsection(f"PHASE 2: ITERATIVE LOOP (Round {round_num + 1}/{self.max_loop_rounds})")
            
    #         # 1. Supervisor Review
    #         context_str = "\n\n".join(global_context)
    #         supervisor_result = await self.supervisor.run(user_query, context_str, current_date, parent_ids=last_node_ids)
            
    #         if supervisor_result.get("last_node_id"):
    #             last_node_ids = [supervisor_result["last_node_id"]]
            
    #         if self.logger:
    #             self.logger.info(f"Round {round_num+1} Supervisor result last_node_id: {supervisor_result.get('last_node_id')}, current last_node_ids: {last_node_ids}")

    #         if supervisor_result["is_sufficient"] or not supervisor_result["sub_queries"]:
    #             if self.logger:
    #                 self.logger.info("Supervisor determined information is sufficient. Proceeding to forecast.")
    #             break
            
    #         # 2. Process Sub-queries
    #         sub_query_tasks = []
    #         for sub_q in supervisor_result["sub_queries"]:
    #             sub_query_tasks.append(self._process_sub_query(sub_q["query"], current_date, parent_ids=last_node_ids))
            
    #         if self.logger:
    #             self.logger.info(f"Processing {len(sub_query_tasks)} sub-queries in parallel...")
            
    #         sub_query_results = await asyncio.gather(*sub_query_tasks)
            
    #         # 3. Update Global Context
    #         new_parent_ids = []
    #         for res in sub_query_results:
    #             global_context.append(f"--- Sub-query: {res['query']} ---\nAnalysis: {res['analysis']}")
    #             if res.get("last_node_id"):
    #                 new_parent_ids.append(res["last_node_id"])
            
    #         if new_parent_ids:
    #             last_node_ids = new_parent_ids
            
    #         if self.logger:
    #             self.logger.info(f"DEBUG: Round {round_num+1} Sub-queries complete. new_parent_ids: {new_parent_ids}, updated last_node_ids: {last_node_ids}")
        
    #     # --- Final Phase ---
    #     if self.logger:
    #         self.logger.subsection("PHASE 3: FINAL FORECAST")
        
    #     final_context_str = "\n\n".join(global_context)
        
    #     # 1. Define Prediction Schema
    #     schema_result = await self.schema_agent.run(user_query, final_context_str, current_date)
        
    #     # 2. Run Community of Researchers (Forecasters)
    #     if self.logger:
    #         self.logger.info(f"Calling Community.run with parent_ids={last_node_ids}")
    #     community_results = await self.community.run(user_query, final_context_str, current_date, schema_result, parent_ids=last_node_ids)
        
    #     # 3. Aggregate Predictions
    #     if isinstance(self.consensus, AgenticConsensus):
    #         # Use LLM-powered evaluation with full researcher outputs
    #         consensus_result = await self.consensus.aggregate_async(
    #             community_results, user_query, schema_result, current_date
    #         )
    #         aggregated_prediction = consensus_result["prediction"]
    #         if self.logger:
    #             self.logger.info(f"[AgenticConsensus] Reasoning: {consensus_result['reasoning'][:300]}...")
    #     else:
    #         # Statistical consensus (mean, median, weighted average)
    #         predictions = [res["prediction"] for res in community_results if "prediction" in res]
    #         aggregated_prediction = self.consensus.aggregate(predictions)
        
    #     if self.logger:
    #         self.logger.info(f"\nFinal Aggregated Prediction: {aggregated_prediction}")
    #         self.logger.save_consensus_data(aggregated_prediction)
    #         self.logger.log_event("Consensus", "final_forecast",
    #                               input_data={"schema": schema_result},
    #                               output_data={"prediction": aggregated_prediction},
    #                               parent_ids=last_node_ids) # Connect to last supervisor/analysis
    #         self.logger.section("EXECUTION COMPLETE")
    #         self.logger.info(f"All data saved to: {self.logger.get_run_dir()}")
        
    #     return {
    #         "question": user_query,
    #         "global_context": final_context_str,
    #         "individual_forecasts": community_results,
    #         "aggregated_prediction": aggregated_prediction
    #     }

    async def _process_sub_query(self, query: str, current_date: str, parent_ids: List[str] = None) -> Dict[str, Any]:
        """Helper to run retrieval and analysis for a single sub-query."""
        retrieval_result = await self.retrieval.run(query, current_date, parent_ids=parent_ids)
        context = retrieval_result.get("summary")

        if self.logger:
            if not context:
                self.logger.error(f"Context is None for sub-query: {query}")

        last_node_ids = [retrieval_result["last_node_id"]] if retrieval_result.get("last_node_id") else []
        
        analysis_result = await self.analyst_agent.run(query, context, current_date, parent_ids=last_node_ids)
        
        return {
            **analysis_result,
            "summary": context
        }

    async def run_research_only(self, user_query: str) -> tuple[str, List[str]]:
        """Runs only the research phases (Initial + Iterative) and returns the context."""
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.section("ITERATIVE RESEARCH WORKFLOW (RESEARCH ONLY)")
            self.logger.info(f"Main Query: {user_query}")
            self.logger.info(f"Max Loop Rounds: {self.max_loop_rounds}")
        
        research_context = []
        final_context = []
        
        # --- Initial Phase ---
        if self.logger:
            self.logger.subsection("PHASE 1: INITIAL RESEARCH")
        
        # 1. Initial Retrieval
        retrieval_result = await self.retrieval.run(user_query, current_date, parent_ids=[])
        initial_context = retrieval_result.get("summary")

        if self.logger:
            if initial_context is None:
                self.logger.error("Initial retrieval returned None for summary")
        
        last_node_ids = [retrieval_result["last_node_id"]] if retrieval_result.get("last_node_id") else []

        try: 
            # 2. Initial Analysis
            analysis_result = await self.analyst_agent.run(user_query, initial_context, current_date, parent_ids=last_node_ids)
            if analysis_result.get("last_node_id"):
                last_node_ids = [analysis_result["last_node_id"]]

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during initial analysis: {e}")
            sys.exit(1)
        
        # Add to global context
        research_context.append(f"--- Initial Research ---\nQuery: {user_query}\nAgentic Retrieval: {initial_context}\nAnalysis: {analysis_result['analysis']}\n Missing Information Analysis: {analysis_result['missing_info']}")
        final_context.append(f"--- Initial Research ---\nQuery: {user_query}\nAgentic Retrieval: {initial_context}\nAnalysis: {analysis_result['analysis']}")
        
        # --- Iterative Loop ---
        for round_num in range(self.max_loop_rounds):            
            if self.logger:
                self.logger.subsection(f"PHASE 2: ITERATIVE LOOP (Round {round_num + 1}/{self.max_loop_rounds})")
            
            # 1. Supervisor Review
            context_str = "\n\n".join(research_context)
            supervisor_result = await self.supervisor.run(user_query, context_str, current_date, parent_ids=last_node_ids)
            
            if supervisor_result.get("last_node_id"):
                last_node_ids = [supervisor_result["last_node_id"]]
            
            if supervisor_result["is_sufficient"] or not supervisor_result["sub_queries"]:
                if self.logger:
                    self.logger.info("Supervisor determined information is sufficient.")
                break
            
            # 2. Process Sub-queries
            sub_query_tasks = []
            for sub_q in supervisor_result["sub_queries"]:
                sub_query_tasks.append(self._process_sub_query(sub_q["query"], current_date, parent_ids=last_node_ids))
            
            if self.logger:
                self.logger.info(f"Processing {len(sub_query_tasks)} sub-queries in parallel...")
            
            sub_query_results = await asyncio.gather(*sub_query_tasks, return_exceptions=True)
            
            # 3. Update Global Context
            new_parent_ids = []
            for i, res in enumerate(sub_query_results):
                if isinstance(res, Exception):
                    if self.logger:
                        self.logger.error(f"Sub-query {i+1} failed with error: {res}")
                    continue
                
                research_context.append(f"--- Sub-query: {res['query']}\nAgentic Retrieval: {res['summary']}\nAnalysis: {res['analysis']}\nMissing Information Analysis: {res['missing_info']}")
                final_context.append(f"--- Sub-query: {res['query']}\nAgentic Retrieval: {res['summary']}\nAnalysis: {res['analysis']}")
                if res.get("last_node_id"):
                    new_parent_ids.append(res["last_node_id"])
            
            if new_parent_ids:
                last_node_ids = new_parent_ids
        
        final_context_str = "\n\n".join(final_context)
        return final_context_str, last_node_ids
