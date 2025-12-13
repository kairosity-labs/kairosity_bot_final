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
)


class SearchQuery(BaseModel):
    """Input search query from AgenticRetrieval"""
    query: str
    rationale: str
    source: str


class OptimizedSearchQuery(BaseModel):
    """Optimized query with source-specific kwargs"""
    
    query: str = Field(description="Optimized query string for the target source")
    kwargs: Dict[str, Union[str, int, float, bool, list, None]] = Field(
        default_factory=dict, 
        description="Source-specific parameters (values can be string, int, float, bool, list, or null)"
    )
    reasoning: str = Field(description="Explanation of optimizations applied")
    
    @classmethod
    def model_json_schema(cls, **kwargs):
        """Override to set additionalProperties: false for kwargs field"""
        schema = super().model_json_schema(**kwargs)
        # Force additionalProperties to false instead of defining types
        if 'properties' in schema and 'kwargs' in schema['properties']:
            schema['properties']['kwargs'] = {
                'type': 'object',
                'description': 'Source-specific parameters',
                'additionalProperties': False,
                'default': {}
            }
        return schema


class MultiOptimizedQueries(BaseModel):
    """Multiple optimized queries for a single source (query expansion)"""
    
    queries: List[OptimizedSearchQuery] = Field(
        description="List of optimized queries, can be 1-3 complementary queries"
    )
    should_expand: bool = Field(
        description="Whether to expand into multiple queries for better coverage"
    )
    
    @classmethod
    def model_json_schema(cls, **kwargs):
        """Override to ensure nested schemas also have additionalProperties: false"""
        schema = super().model_json_schema(**kwargs)
        
        # Fix the nested OptimizedSearchQuery schema if it exists in $defs
        if '$defs' in schema and 'OptimizedSearchQuery' in schema['$defs']:
            osq_schema = schema['$defs']['OptimizedSearchQuery']
            if 'properties' in osq_schema and 'kwargs' in osq_schema['properties']:
                osq_schema['properties']['kwargs'] = {
                    'type': 'object',
                    'description': 'Source-specific parameters',
                    'additionalProperties': False,
                    'default': {}
                }
        
        return schema



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
    }
    
    def __init__(self, backend: BaseBackend, logger=None):
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
            self._optimize_single_query(sq, user_query, current_date)
            for sq in search_queries
        ]
        
        results = await asyncio.gather(*optimization_tasks, return_exceptions=True)
        
        # Flatten results (since each optimization can return 1-3 queries)
        optimized_queries = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                if self.logger:
                    self.logger.error(f"Optimization failed for query {i+1}: {type(result).__name__}")
                    self.logger.error(f"Exception details: {str(result)}")
                    self.logger.error(f"Traceback: {''.join(traceback.format_exception(type(result), result, result.__traceback__))}")
                # Fallback: use original query with empty kwargs
                optimized_queries.append(OptimizedSearchQuery(
                    query=search_queries[i].query,
                    kwargs={},
                    reasoning="Optimization failed, using original query"
                ))
            else:
                # Result is a MultiOptimizedQueries object
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
        current_date: str
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
                    kwargs={},
                    reasoning=f"No optimization available for {source}"
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
                max_tokens=2048
            )
            
            if self.logger:
                for i, oq in enumerate(multi_queries.queries):
                    prefix = f"  [{i+1}]" if len(multi_queries.queries) > 1 else "  ✓"
                    self.logger.info(f"{prefix} '{search_query.query}' → '{oq.query}'")
                    if oq.kwargs:
                        self.logger.info(f"      kwargs: {oq.kwargs}")
            
            return multi_queries
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to optimize query '{search_query.query}': {e}")
            # Fallback
            return MultiOptimizedQueries(
                queries=[OptimizedSearchQuery(
                    query=search_query.query,
                    kwargs={},
                    reasoning=f"Optimization failed: {str(e)}"
                )],
                should_expand=False
            )
