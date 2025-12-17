import asyncio
import random
import traceback
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, field_validator
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
    
    @field_validator('search_queries', mode='before')
    @classmethod
    def ensure_search_queries_not_none(cls, v):
        """Ensure search_queries is never None"""
        if v is None:
            raise ValueError("search_queries cannot be None, must be a list of SearchQuery")
        return v

class AgenticRetrieval:
    def __init__(self, backend: BaseBackend, data_mcps: Dict[str, BaseDataMCP], max_rounds: int = 3, max_queries: int = 10, max_tokens: int = 16384, logger=None):
        self.backend = backend
        self.data_mcps = data_mcps
        self.max_rounds = max_rounds
        self.max_queries = max_queries
        self.max_tokens = max_tokens
        self.logger = logger
        
        # Initialize Query Optimizer
        self.query_optimizer = QueryOptimizer(backend, max_tokens=max_tokens, logger=logger)

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
                    max_tokens = self.max_tokens if retry == 0 else 2 * self.max_tokens
                    step_plan = await self.backend.generate_structured(messages, RetrievalStep, max_tokens=max_tokens)
                    break  # Success, exit retry loop
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Failed to generate retrieval step plan (attempt {retry + 1}/{max_retries}): {e}")
                        self.logger.error(f"Exception type: {type(e).__name__}")
                        self.logger.error(f"Full traceback:\n{''.join(traceback.format_exception(type(e), e, e.__traceback__))}")
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
            
            # Randomly sample queries if they exceed max_queries to prevent context explosion
            if len(optimized_queries) > self.max_queries:
                if self.logger:
                    self.logger.info(f"⚠️  Generated {len(optimized_queries)} queries exceeds max_queries={self.max_queries}")
                    self.logger.info(f"📊 Randomly sampling {self.max_queries} queries for execution")
                sampled_queries = random.sample(optimized_queries, self.max_queries)
            else:
                sampled_queries = optimized_queries
            
            # Log optimization results
            if self.logger:
                self.logger.info(f"Generated {len(optimized_queries)} optimized queries (from {len(step_plan.search_queries)} original)")
                if len(sampled_queries) < len(optimized_queries):
                    self.logger.info(f"Executing {len(sampled_queries)}/{len(optimized_queries)} sampled queries")
                optimization_node_id = self.logger.log_event(
                    "AgenticRetrieval", 
                    "query_optimization",
                    input_data={
                        "original_queries": [sq.dict() for sq in step_plan.search_queries],
                        "round": round_num + 1,
                        "max_queries": self.max_queries
                    },
                    output_data={
                        "all_optimized_queries": [oq.dict() for oq in optimized_queries],
                        "sampled_queries": [oq.dict() for oq in sampled_queries],
                        "total_generated": len(optimized_queries),
                        "total_sampled": len(sampled_queries)
                    },
                    parent_ids=[reasoning_node_id]
                )
                # Optimization node becomes parent for searches
                current_parent_ids = [optimization_node_id]
            
            # 3. Execute sampled search queries in parallel
            if self.logger:
                self.logger.info(f"Executing {len(sampled_queries)} search queries...")
            
            search_tasks = []
            
            for i, opt_query in enumerate(sampled_queries):
                original_query = step_plan.search_queries[opt_query.original_index]
                source = original_query.source
                
                if source in self.data_mcps:
                    mcp = self.data_mcps[source]
                    search_tasks.append((
                        i, 
                        original_query, 
                        opt_query, 
                        mcp.search(opt_query.query)
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
                    opt_query_str = opt_query.query
                    self.logger.save_query_data(
                        round_num + 1,
                        query_idx + 1,
                        opt_query_str,
                        original_query.source,
                        result
                    )
                    self.logger.info(f"Retrieved {len(result)} results from search {query_idx + 1}")
                    self.logger.info(f"  Original: '{original_query.query}'")
                    self.logger.info(f"  Optimized: '{opt_query_str}'")
                    
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
                            "optimized_query": opt_query_str,
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
            {"role": "system", "content": AGENTIC_RETRIEVAL_SUMMARY_SYSTEM_PROMPT.format(
                current_date=current_date,
                user_query=user_query
            )},
            {"role": "user", "content": AGENTIC_RETRIEVAL_SUMMARY_USER_PROMPT.format(
                user_query=user_query, 
                retrieved_info=final_context
            )}
        ]
        
        # Generate summary with retry logic
        final_summary = None
        max_retries = 3
        for retry in range(max_retries):
            try:
                final_summary = await self.backend.generate(summary_messages, max_tokens=self.max_tokens)
                
                # Ensure summary is not None or empty
                if final_summary and final_summary.strip() != "":
                    break  # Success, exit retry loop
                else:
                    if self.logger:
                        self.logger.warning(f"Generated summary is None or empty (attempt {retry + 1}/{max_retries})")
                    if retry < max_retries - 1:
                        # Wait before retrying (exponential backoff: 2, 4, 8 seconds)
                        wait_time = 2 ** (retry + 1)
                        if self.logger:
                            self.logger.info(f"Retrying summary generation in {wait_time}s...")
                        await asyncio.sleep(wait_time)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to generate final summary (attempt {retry + 1}/{max_retries}): {e}")
                if retry < max_retries - 1:
                    # Wait before retrying
                    wait_time = 2 ** (retry + 1)
                    if self.logger:
                        self.logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
        
        # If all retries failed, use fallback summary
        if not final_summary or final_summary.strip() == "":
            if self.logger:
                self.logger.warning("All retries failed for summary generation, using fallback")
            final_summary = f"Research summary for: {user_query}\n\nFound {len(all_retrieved_data)} results across {round_num + 1} rounds of retrieval."
        
        summary_node_id = None
        if self.logger:
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
        
        # Debug: Check if summary is None before returning
        if self.logger and result.get("summary") is None:
            self.logger.error(f"WARNING: AgenticRetrieval returning None summary for query: {user_query[:100]}")
        
        return result
