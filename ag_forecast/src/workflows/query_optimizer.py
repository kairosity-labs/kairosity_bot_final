import asyncio
import traceback
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from ag_forecast.src.backends.base import BaseBackend
from ag_forecast.src.prompts import (
    QUERY_OPTIMIZER_SYSTEM_PROMPT,
    GOOGLE_SEARCH_OPTIMIZATION_PROMPT,
    GOOGLE_SCRAPE_OPTIMIZATION_PROMPT,
    PERPLEXITY_SEARCH_OPTIMIZATION_PROMPT,
    PERPLEXITY_SONAR_OPTIMIZATION_PROMPT,
    ASKNEWS_OPTIMIZATION_PROMPT,
    DUCKDUCKGO_OPTIMIZATION_PROMPT,
    PARALLEL_OPTIMIZATION_PROMPT,
)


class SearchQuery(BaseModel):
    """Input search query from AgenticRetrieval"""
    query: str
    rationale: str
    source: str


class OptimizedSearchQuery(BaseModel):
    """Optimized query with source-specific details"""
    query: str = Field(description="The optimized search query string")
    reasoning: str = Field(description="Explanation of optimizations applied")
    original_index: int = Field(description="Index of the original SearchQuery that generated this optimized query")


class MultiOptimizedQueries(BaseModel):
    """Multiple optimized queries for a single source (query expansion)"""
    
    queries: List[OptimizedSearchQuery] = Field(
        description="List of optimized queries, can be 1-3 complementary queries"
    )
    should_expand: bool = Field(
        description="Whether to expand into multiple queries for better coverage"
    )
    
    @field_validator('queries', mode='before')
    @classmethod
    def ensure_queries_not_none(cls, v):
        """Ensure queries is never None, use empty list as fallback"""
        if v is None:
            raise ValueError("queries cannot be None, must be a list of OptimizedSearchQuery")
        return v


class QueryOptimizer:
    """
    Optimizes search queries for specific data MCPs.
    
    Transforms generic queries into source-specific optimized queries with:
    - Keyword optimization for search engines
    - Natural language formatting for AI assistants
    - Context-aware date extraction
    - Domain suggestions for trusted sources
    - Multi-query expansion for complex topics
    """
    
    # Map sources to their optimization prompts
    SOURCE_PROMPTS = {
        "google_search": GOOGLE_SEARCH_OPTIMIZATION_PROMPT,
        "google_scrape": GOOGLE_SCRAPE_OPTIMIZATION_PROMPT,
        "perplexity_search": PERPLEXITY_SEARCH_OPTIMIZATION_PROMPT,
        "perplexity_sonar": PERPLEXITY_SONAR_OPTIMIZATION_PROMPT,
        "asknews": ASKNEWS_OPTIMIZATION_PROMPT,
        "duckduckgo": DUCKDUCKGO_OPTIMIZATION_PROMPT,
        "parallel": PARALLEL_OPTIMIZATION_PROMPT,
    }
    
    def __init__(self, backend: BaseBackend, max_tokens: int = 16384, logger=None):
        self.max_tokens = max_tokens
        self.backend = backend
        self.logger = logger
    
    async def optimize_queries(
        self, 
        search_queries: List[SearchQuery], 
        user_query: str, 
        current_date: str
    ) -> List[OptimizedSearchQuery]:
        """
        Optimize a batch of search queries for their respective sources.
        
        Args:
            search_queries: List of SearchQuery objects from AgenticRetrieval
            user_query: The original user query for context
            current_date: Current date string for temporal context
            
        Returns:
            List of OptimizedSearchQuery objects (may be more than input if queries are expanded)
        """
        if self.logger:
            self.logger.info(f"\n🔧 Optimizing {len(search_queries)} search queries...")
        
        # Process all queries in parallel with multi-query expansion support
        optimization_tasks = [
            self._optimize_single_query(sq, user_query, current_date, i)
            for i, sq in enumerate(search_queries)
        ]
        
        results = await asyncio.gather(*optimization_tasks, return_exceptions=True)
        
        # Flatten results
        optimized_queries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                if self.logger:
                    self.logger.error(f"Optimization failed for query {i+1}: {type(result).__name__}")
                    self.logger.error(f"Exception details: {str(result)}")
                    self.logger.error(f"Traceback: {''.join(traceback.format_exception(type(result), result, result.__traceback__))}")
                # Fallback: use original query
                optimized_queries.append(OptimizedSearchQuery(
                    query=search_queries[i].query,
                    reasoning="Optimization failed, using original query",
                    original_index=i
                ))
            else:
                # Result is a MultiOptimizedQueries object
                for oq in result.queries:
                    # Validate query is not empty
                    if not oq.query or not oq.query.strip():
                        oq.query = search_queries[i].query
                
                optimized_queries.extend(result.queries)
                if self.logger and result.should_expand and len(result.queries) > 1:
                    self.logger.info(f"  ↳ Expanded into {len(result.queries)} complementary queries")
        
        if self.logger:
            self.logger.info(f"✓ Generated {len(optimized_queries)} optimized queries (from {len(search_queries)} original)")
        
        return optimized_queries
    
    async def _optimize_single_query(
        self, 
        search_query: SearchQuery, 
        user_query: str, 
        current_date: str,
        original_index: int
    ) -> MultiOptimizedQueries:
        """
        Optimize a single search query for its target source.
        
        Returns MultiOptimizedQueries which may contain 1-3 optimized queries.
        """
        source = search_query.source
        
        # Get source-specific optimization prompt
        if source not in self.SOURCE_PROMPTS:
            if self.logger:
                self.logger.warning(f"No optimization prompt for source '{source}', using original query")
            return MultiOptimizedQueries(
                queries=[OptimizedSearchQuery(
                    query=search_query.query,
                    reasoning=f"No optimization available for {source}",
                    original_index=original_index
                )],
                should_expand=False
            )
        
        source_prompt = self.SOURCE_PROMPTS[source]
        
        # Build messages for LLM
        messages = [
            {
                "role": "system", 
                "content": QUERY_OPTIMIZER_SYSTEM_PROMPT.format(
                    current_date=current_date,
                    source=source
                )
            },
            {
                "role": "user", 
                "content": source_prompt.format(
                    user_query=user_query,
                    original_query=search_query.query,
                    rationale=search_query.rationale,
                    current_date=current_date
                )
            }
        ]
        
        # Generate structured output
        try:
            multi_queries = await self.backend.generate_structured(
                messages, 
                MultiOptimizedQueries,
                max_tokens=self.max_tokens
            )
            
            for oq in multi_queries.queries:
                oq.original_index = original_index
            
            if self.logger:
                for i, oq in enumerate(multi_queries.queries):
                    prefix = f"  [{i+1}]" if len(multi_queries.queries) > 1 else "  ✓"
                    self.logger.info(f"{prefix} '{search_query.query}' → '{oq.query}'")
            
            return multi_queries
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to optimize query '{search_query.query}': {e}")
            # Fallback
            return MultiOptimizedQueries(
                queries=[OptimizedSearchQuery(
                    query=search_query.query,
                    reasoning=f"Optimization failed: {str(e)}",
                    original_index=original_index
                )],
                should_expand=False
            )
