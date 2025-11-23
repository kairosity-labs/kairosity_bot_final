import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.data_mcps.base import BaseDataMCP
from ag_forecast.src.prompts import (
    AGENTIC_RETRIEVAL_SYSTEM_PROMPT,
    AGENTIC_RETRIEVAL_USER_PROMPT,
    AGENTIC_RETRIEVAL_SUMMARY_SYSTEM_PROMPT,
    AGENTIC_RETRIEVAL_SUMMARY_USER_PROMPT
)

class SearchQuery(BaseModel):
    query: str
    rationale: str
    source: str  # e.g., "perplexity", "asknews", "duckduckgo"

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

    async def run(self, user_query: str, current_date: str = None) -> Dict[str, Any]:
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
        
        for round_num in range(self.max_rounds):
            if self.logger:
                self.logger.info(f"\n--- Round {round_num + 1}/{self.max_rounds} ---")
            
            # Build context string from Q&A pairs
            context_str = "\n\n".join([
                f"Q: {qa['query']}\nA: {qa['answer']}" 
                for qa in qa_pairs
            ]) if qa_pairs else "No information retrieved yet."
            
            # 1. Reason and generate search queries
            messages = [
                {"role": "system", "content": AGENTIC_RETRIEVAL_SYSTEM_PROMPT.format(
                    current_date=current_date,
                    user_query=user_query, 
                    sources=list(self.data_mcps.keys())
                )},
                {"role": "user", "content": AGENTIC_RETRIEVAL_USER_PROMPT.format(context=context_str)}
            ]
            
            step_plan = await self.backend.generate_structured(messages, RetrievalStep)
            
            if self.logger:
                self.logger.info(f"Reasoning: {step_plan.reasoning}")
                self.logger.info(f"Is sufficient: {step_plan.is_sufficient}")
                self.logger.log_event("AgenticRetrieval", "reasoning", 
                                      input_data={"round": round_num+1, "context": context_str},
                                      output_data=step_plan.dict())
            
            if step_plan.is_sufficient:
                if self.logger:
                    self.logger.info("Agent determined information is sufficient. Stopping retrieval.")
                break
            
            # 2. Execute search queries in parallel
            if self.logger:
                self.logger.info(f"Generated {len(step_plan.search_queries)} search queries")
                for i, sq in enumerate(step_plan.search_queries):
                    self.logger.info(f"  - Query: '{sq.query}' via {sq.source} (Rationale: {sq.rationale})")
            
            search_tasks = []
            for i, search_query in enumerate(step_plan.search_queries):
                if search_query.source in self.data_mcps:
                    mcp = self.data_mcps[search_query.source]
                    search_tasks.append((i, search_query, mcp.search(search_query.query)))
            
            results = await asyncio.gather(*[task for _, _, task in search_tasks], return_exceptions=True)
            
            # Process results and build Q&A pairs
            for (query_idx, search_query, _), result in zip(search_tasks, results):
                if isinstance(result, Exception):
                    if self.logger:
                        self.logger.error(f"Search failed: {result}")
                    continue
                
                # Save individual query data
                if self.logger:
                    self.logger.save_query_data(
                        round_num + 1,
                        query_idx + 1,
                        search_query.query,
                        search_query.source,
                        result
                    )
                    self.logger.info(f"Retrieved {len(result)} results from search {query_idx + 1}")
                    self.logger.log_event("AgenticRetrieval", "search_result",
                                          input_data={"query": search_query.query, "source": search_query.source},
                                          output_data=result)
                
                all_retrieved_data.extend(result)
                
                # Build Q&A pair for this query
                answer = "\n".join([item.get("content", "") for item in result])
                qa_pairs.append({
                    "query": search_query.query,
                    "answer": answer,
                    "source": search_query.source
                })
        
        # 3. Generate final summary
        if self.logger:
            self.logger.info(f"\nGenerating final summary from {len(all_retrieved_data)} total results...")
        
        # Build final context with all Q&A pairs
        final_context = "\n\n".join([
            f"Q: {qa['query']}\nA: {qa['answer']}" 
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
            self.logger.log_event("AgenticRetrieval", "summary",
                                  input_data={"user_query": user_query, "retrieved_count": len(all_retrieved_data)},
                                  output_data=final_summary)
        
        result = {
            "query": user_query,
            "retrieved_data": all_retrieved_data,
            "qa_pairs": qa_pairs,
            "summary": final_summary,
            "rounds_used": round_num + 1
        }
        
        # Save structured data
        if self.logger:
            self.logger.save_retrieval_data(user_query, all_retrieved_data, final_summary)
        
        # Return context as Q&A pairs + summary for researchers
        context_for_researchers = final_context + "\n\n=== SUMMARY ===\n" + final_summary
        result["context_for_researchers"] = context_for_researchers
        
        return result
