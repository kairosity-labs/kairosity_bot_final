import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.data_mcps.base import BaseDataMCP
from ag_forecast.src.prompts import (
    AGENTIC_RETRIEVAL_SYSTEM_PROMPT,
    get_agentic_retrieval_user_prompt,
    AGENTIC_RETRIEVAL_SUMMARY_SYSTEM_PROMPT,
    AGENTIC_RETRIEVAL_SUMMARY_USER_PROMPT
)
from ag_forecast.src.workflows.query_optimizer import QueryOptimizer

class SearchQuery(BaseModel):
    query: str
    rationale: str
    source: str

class RetrievalStep(BaseModel):
    reasoning: str
    search_queries: List[SearchQuery]
    is_sufficient: bool

class AgenticRetrieval:
    def __init__(self, backend: BaseBackend, data_mcps: Dict[str, BaseDataMCP], max_rounds: int = 3, logger=None):
        self.backend = backend
        self.data_mcps = data_mcps
        self.max_rounds = max_rounds
        self.logger = logger
        
        # Initialize Query Optimizer
        self.query_optimizer = QueryOptimizer(backend, logger)

    async def run(self, user_query: str, current_date: str = None, parent_ids: List[str] = None) -> Dict[str, Any]:
        from datetime import datetime
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.logger:
            self.logger.subsection("AGENTIC RETRIEVAL")
            self.logger.info(f"Query: {user_query}")
            self.logger.info(f"Current Date: {current_date}")
            self.logger.info(f"Max rounds: {self.max_rounds}")
            self.logger.info(f"Available sources: {list(self.data_mcps.keys())}")
        
        # Build context as Q&A pairs
        qa_pairs = []
        all_retrieved_data = []
        
        # Track the last set of node IDs to connect the next step to
        current_parent_ids = parent_ids or []
        
        for round_num in range(self.max_rounds):
            if self.logger:
                self.logger.info(f"\n--- Round {round_num + 1}/{self.max_rounds} ---")
            
            # Build context string from Q&A pairs
            context_str = "\n\n".join([
                f"Q: {qa['query']}\nA: {qa['answer']}" 
                for qa in qa_pairs
            ]) if qa_pairs else "No information retrieved yet."
            
            # 1. Reason and generate search queries
            # Generate dynamic user prompt based on available MCPs
            user_prompt = get_agentic_retrieval_user_prompt(list(self.data_mcps.keys()))
            
            messages = [
                {"role": "system", "content": AGENTIC_RETRIEVAL_SYSTEM_PROMPT.format(
                    current_date=current_date,
                    user_query=user_query, 
                    sources=list(self.data_mcps.keys())
                )},
                {"role": "user", "content": user_prompt.format(query=user_query, context=context_str)}
            ]
            
            # Try to generate structured output with retry logic
            step_plan = None
            max_retries = 2
            for retry in range(max_retries):
                try:
                    # Increase max_tokens on retry
                    max_tokens = 4096 if retry == 0 else 8192
                    step_plan = await self.backend.generate_structured(messages, RetrievalStep, max_tokens=max_tokens)
                    break  # Success, exit retry loop
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to generate retrieval step plan (attempt {retry + 1}/{max_retries}): {e}")
                    if retry == max_retries - 1:
                        # Last retry failed, skip this round
                        if self.logger:
                            self.logger.error("All retries exhausted. Skipping round.")
                        continue
            
            if not step_plan:
                if self.logger:
                    self.logger.error("Failed to generate retrieval step plan (parsed response is None). Skipping round.")
                continue

            if self.logger:
                self.logger.info(f"Reasoning: {step_plan.reasoning}")
                self.logger.info(f"Is sufficient: {step_plan.is_sufficient}")
                self.logger.info(f"Is sufficient: {step_plan.is_sufficient}")
                reasoning_node_id = self.logger.log_event("AgenticRetrieval", "reasoning", 
                                      input_data={"round": round_num+1, "context": context_str},
                                      output_data=step_plan.dict(),
                                      parent_ids=current_parent_ids)
                # The reasoning node becomes the parent for the searches
                current_parent_ids = [reasoning_node_id]
            
            if step_plan.is_sufficient:
                if self.logger:
                    self.logger.info("Agent determined information is sufficient. Stopping retrieval.")
                break
            
            # 2. Optimize queries for each source
            if self.logger:
                self.logger.info(f"\nOptimizing {len(step_plan.search_queries)} search queries...")
            
            optimized_queries = await self.query_optimizer.optimize_queries(
                step_plan.search_queries,
                user_query,
                current_date
            )
            
            # Log optimization results
            if self.logger:
                self.logger.info(f"Generated {len(optimized_queries)} optimized queries (from {len(step_plan.search_queries)} original)")
                optimization_node_id = self.logger.log_event(
                    "AgenticRetrieval", 
                    "query_optimization",
                    input_data={
                        "original_queries": [sq.dict() for sq in step_plan.search_queries],
                        "round": round_num + 1
                    },
                    output_data=[oq.dict() for oq in optimized_queries],
                    parent_ids=[reasoning_node_id]
                )
                # Optimization node becomes parent for searches
                current_parent_ids = [optimization_node_id]
            
            # 3. Execute optimized search queries in parallel
            if self.logger:
                self.logger.info(f"Executing {len(optimized_queries)} search queries...")
            
            search_tasks = []
            # Build mapping from optimized queries back to original for logging
            query_mapping = {}  # Maps optimized query index to original SearchQuery
            
            for i, opt_query in enumerate(optimized_queries):
                # Find corresponding original query (handle multi-query expansion)
                # For now, we'll create a pseudo original query for expanded queries
                original_idx = min(i, len(step_plan.search_queries) - 1)
                original_query = step_plan.search_queries[original_idx]
                query_mapping[i] = original_query
                
                # Determine source from the original query
                source = original_query.source
                
                if source in self.data_mcps:
                    mcp = self.data_mcps[source]
                    search_tasks.append((
                        i, 
                        original_query, 
                        opt_query, 
                        mcp.search(opt_query.query, **opt_query.kwargs)
                    ))
                else:
                    if self.logger:
                        self.logger.warning(f"Source '{source}' not available in data_mcps, skipping query {i+1}")
            
            results = await asyncio.gather(*[task for _, _, _, task in search_tasks], return_exceptions=True)
            
            # Process results and build Q&A pairs
            for (query_idx, original_query, opt_query, _), result in zip(search_tasks, results):
                if isinstance(result, Exception):
                    if self.logger:
                        self.logger.error(f"Search failed: {result}")
                    continue
                
                # Save individual query data
                if self.logger:
                    self.logger.save_query_data(
                        round_num + 1,
                        query_idx + 1,
                        opt_query.query,
                        original_query.source,
                        result
                    )
                    self.logger.info(f"Retrieved {len(result)} results from search {query_idx + 1}")
                    self.logger.info(f"  Original: '{original_query.query}'")
                    self.logger.info(f"  Optimized: '{opt_query.query}'")
                    if opt_query.kwargs:
                        self.logger.info(f"  Kwargs: {opt_query.kwargs}")
                    # Log actual result details for proof
                    if result:
                        self.logger.info(f"  Results from {original_query.source}:")
                        for idx, item in enumerate(result[:3], 1):  # Show first 3 results
                            title = item.get("title", "No title")
                            url = item.get("url", "No URL")
                            self.logger.info(f"    {idx}. {title}")
                            self.logger.info(f"       URL: {url}")
                    search_node_id = self.logger.log_event(
                        "AgenticRetrieval", 
                        "search_result",
                        input_data={
                            "original_query": original_query.query,
                            "optimized_query": opt_query.query,
                            "kwargs": opt_query.kwargs,
                            "source": original_query.source
                        },
                        output_data=result,
                        parent_ids=current_parent_ids  # Connect to optimization node
                    )
                    
                    # Collect search node IDs for the next step (Summary)
                    if query_idx == 0:
                        current_parent_ids = [] # Reset for this batch of searches
                    current_parent_ids.append(search_node_id)
                
                all_retrieved_data.extend(result)
                
                # Build Q&A pair for this query
                answer = "\n".join([item.get("content", "") for item in result])
                qa_pairs.append({
                    "query": original_query.query,
                    "answer": answer,
                    "source": original_query.source
                })
        
        # 3. Generate final summary
        if self.logger:
            self.logger.info(f"\nGenerating final summary from {len(all_retrieved_data)} total results...")
        
        # Build final context with all Q&A pairs
        final_context = "\n\n".join([
            f"Search Query: {qa['query']}\nAnswer: {qa['answer']}\nSource: {qa['source']}" 
            for qa in qa_pairs
        ])
        
        summary_messages = [
            {"role": "system", "content": AGENTIC_RETRIEVAL_SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": AGENTIC_RETRIEVAL_SUMMARY_USER_PROMPT.format(
                user_query=user_query, 
                retrieved_info=final_context
            )}
        ]
        
        final_summary = await self.backend.generate(summary_messages)
        
        if self.logger:
            self.logger.info(f"Summary: {final_summary[:500]}...")
            self.logger.info(f"Summary: {final_summary[:500]}...")
            summary_node_id = self.logger.log_event("AgenticRetrieval", "summary",
                                  input_data={"user_query": user_query, "retrieved_count": len(all_retrieved_data)},
                                  output_data=final_summary,
                                  parent_ids=current_parent_ids) # Connects to last search results
        
        result = {
            "query": user_query,
            "retrieved_data": all_retrieved_data,
            "qa_pairs": qa_pairs,
            "summary": final_summary,
            "rounds_used": round_num + 1,
            "last_node_id": summary_node_id
        }
        
        # Save structured data
        if self.logger:
            self.logger.save_retrieval_data(user_query, all_retrieved_data, final_summary)
        
        # Return context as Q&A pairs + summary for researchers
        context_for_researchers = final_context + "\n\n=== SUMMARY ===\n" + final_summary
        result["context_for_researchers"] = context_for_researchers
        
        return result
