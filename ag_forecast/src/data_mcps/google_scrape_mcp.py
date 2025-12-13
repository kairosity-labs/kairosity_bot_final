from typing import List, Dict, Any
from urllib.parse import urlparse
from ..data_mcps.base import BaseDataMCP
from ..data_mcps.google_search_mcp import GoogleSearchMCP
from ..utils.content_extractor import ContentExtractor


class GoogleScrapeMCP(BaseDataMCP):
    """Google Search + Deep Content Extraction with smart filtering and ranking."""
    
    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)
        self.search_mcp = GoogleSearchMCP()
        self.content_extractor = ContentExtractor()

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        is_news = kwargs.get('is_news', False)
        date_before = kwargs.get('date_before')
        max_summaries = kwargs.get('max_summaries', 10)
        
        # Get search results
        search_results = await self.search_mcp.search(
            query, 
            is_news=is_news, 
            date_before=date_before, 
            max_results=max_summaries * 3  # Get more to filter
        )
        
        if not search_results:
            return []
        
        # Smart URL filtering
        filtered_urls = self._filter_urls(search_results)
        
        # Extract content
        extraction_results = await self.content_extractor.extract(filtered_urls[:max_summaries * 2])
        
        # Build final results with metadata
        final_results = []
        for url, data in extraction_results.items():
            if not data.get('success') or not data.get('content'):
                continue
            
            content = data['content'].strip()
            if len(content.split()) < 150:  # Increased threshold
                continue
            
            search_result = next((r for r in search_results if r['url'] == url), {})
            
            final_results.append({
                "title": search_result.get('title', ''),
                "url": url,
                "content": content,
                "date": search_result.get('date', 'Unknown'),
                "domain": data.get('domain', ''),
                "source": "google_scrape",
                "quality_score": data.get('quality_score', 50),
                "metadata": data.get('metadata', {})
            })
        
        # Rank by quality
        ranked_results = self._rank_results(final_results)
        
        return ranked_results[:max_summaries]

    def _filter_urls(self, search_results: List[dict]) -> List[str]:
        """Filter out low-quality URLs."""
        skip_extensions = ['.pdf', '.doc', '.ppt', '.xls', '.zip', '.mp4', '.mp3']
        skip_domains = [
            'facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com',
            'youtube.com', 'linkedin.com', 'reddit.com', 'pinterest.com'
        ]
        
        filtered = []
        for result in search_results:
            url = result.get('url', '')
            
            # Skip bad extensions
            if any(url.lower().endswith(ext) for ext in skip_extensions):
                continue
            
            # Skip social media
            if any(domain in url.lower() for domain in skip_domains):
                continue
            
            filtered.append(url)
        
        return filtered

    def _rank_results(self, results: List[dict]) -> List[dict]:
        """Rank results by quality, recency, and domain authority."""
        
        # Domain credibility scores
        tier1_domains = ['reuters.com', 'apnews.com', 'bbc.com', 'nature.com', 'science.org']
        tier2_domains = ['cnn.com', 'theguardian.com', 'bloomberg.com', 'nytimes.com', 'wsj.com']
        
        scored_results = []
        for result in results:
            score = result.get('quality_score', 50)
            
            # Domain bonus
            domain = result.get('domain', '').lower()
            if any(d in domain for d in tier1_domains):
                score += 20
            elif any(d in domain for d in tier2_domains):
                score += 10
            
            # Recency bonus (if date is not Unknown)
            if result.get('date') != 'Unknown':
                score += 5
            
            # Content length bonus (longer is better, up to a point)
            content_len = len(result.get('content', ''))
            if content_len > 2000:
                score += 10
            elif content_len > 1000:
                score += 5
            
            scored_results.append((result, score))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return [r for r, _ in scored_results]
