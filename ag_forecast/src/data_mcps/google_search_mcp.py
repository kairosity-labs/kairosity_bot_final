import asyncio
import re
from typing import List, Dict, Any
from datetime import datetime
from patchright.async_api import async_playwright
from bs4 import BeautifulSoup
from ..data_mcps.base import BaseDataMCP


class GoogleSearchMCP(BaseDataMCP):
    """Google Search via Patchright browser scraping."""
    
    _semaphore = asyncio.Semaphore(2)
    
    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)

    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        query = query.replace('"', '').replace("'", '').strip()
        is_news = kwargs.get('is_news', False)
        date_before = kwargs.get('date_before')
        max_results = kwargs.get('max_results', 20)
        
        # Retry logic with exponential backoff for robustness
        max_retries = 3
        base_delay = 5  # Start with 5 seconds
        
        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    # Respectful rate limiting - increase delay between requests
                    await asyncio.sleep(3 if attempt == 0 else base_delay * (2 ** (attempt - 1)))
                    
                    search_url = self._build_search_url(query, is_news, date_before)
                    
                    if hasattr(self, 'logger') and self.logger and attempt > 0:
                        self.logger.info(f"Retry attempt {attempt + 1}/{max_retries} for query: {query}")
                    
                    async with async_playwright() as p:
                        # Launch with more realistic settings
                        browser = await p.chromium.launch(
                            headless=True,
                            args=[
                                '--disable-blink-features=AutomationControlled',
                                '--no-sandbox',
                                '--disable-dev-shm-usage'
                            ]
                        )
                        
                        # Create context with realistic fingerprint
                        context = await browser.new_context(
                            viewport={'width': 1920, 'height': 1080},
                            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            locale='en-US',
                            timezone_id='America/New_York',
                            permissions=['geolocation'],
                            geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
                            extra_http_headers={
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                                'Accept-Encoding': 'gzip, deflate, br',
                                'DNT': '1',
                                'Connection': 'keep-alive',
                                'Upgrade-Insecure-Requests': '1'
                            }
                        )
                        
                        page = await context.new_page()
                        
                        # Override navigator.webdriver
                        await page.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                            
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => [1, 2, 3, 4, 5]
                            });
                            
                            Object.defineProperty(navigator, 'languages', {
                                get: () => ['en-US', 'en']
                            });
                        """)
                        
                        try:
                            # For news, wait longer for content to load
                            wait_until = 'networkidle' if is_news else 'domcontentloaded'
                            await page.goto(search_url, wait_until=wait_until, timeout=30000)
                            
                            # Extra wait for news to ensure all content loads
                            await asyncio.sleep(4 if is_news else 2)
                            html = await page.content()
                        finally:
                            await browser.close()
                    
                    # CAPTCHA Detection
                    html_lower = html.lower()
                    if 'captcha' in html_lower or 'unusual traffic' in html_lower:
                        if hasattr(self, 'logger') and self.logger:
                            self.logger.warning(f"CAPTCHA detected on attempt {attempt + 1} for query: {query}")
                        
                        # If this is the last attempt, return empty results
                        if attempt == max_retries - 1:
                            if hasattr(self, 'logger') and self.logger:
                                self.logger.error(f"CAPTCHA persists after {max_retries} attempts. Returning empty results.")
                            return []
                        
                        # Otherwise, retry with longer delay
                        continue
                    
                    # Rate Limit Detection
                    if '429' in html or 'too many requests' in html_lower:
                        if hasattr(self, 'logger') and self.logger:
                            self.logger.warning(f"Rate limit detected on attempt {attempt + 1}. Waiting before retry...")
                        
                        if attempt == max_retries - 1:
                            if hasattr(self, 'logger') and self.logger:
                                self.logger.error(f"Rate limit persists. Returning empty results.")
                            return []
                        
                        # Longer wait for rate limits
                        await asyncio.sleep(base_delay * 2)
                        continue
                    
                    # Successfully got HTML, parse it
                    results = self._parse_results(html, is_news, date_before, max_results)
                    
                    # If we got results, success!
                    if results:
                        return results
                    
                    # If no results but no CAPTCHA, might be legitimate empty results
                    if hasattr(self, 'logger') and self.logger:
                        self.logger.debug(f"No results found for query: {query}")
                    return []
                    
            except Exception as e:
                if hasattr(self, 'logger') and self.logger:
                    self.logger.error(f"Error on attempt {attempt + 1} for query '{query}': {str(e)}")
                
                # If last attempt, return empty results
                if attempt == max_retries - 1:
                    if hasattr(self, 'logger') and self.logger:
                        self.logger.error(f"All {max_retries} attempts failed for query: {query}")
                    return []
                
                # Otherwise wait and retry
                await asyncio.sleep(base_delay * (2 ** attempt))
        
        # Fallback (should never reach here)
        return []

    def _build_search_url(self, query: str, is_news: bool, date_before: str) -> str:
        base = "https://www.google.com/search"
        params = [f"q={query.replace(' ', '+')}"]
        
        if is_news:
            params.append("tbm=nws")
        
        if date_before:
            params.append(f"tbs=cdr:1,cd_max:{date_before}")
        
        return f"{base}?{'&'.join(params)}"

    def _parse_results(self, html: str, is_news: bool, date_before: str, max_results: int) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Debug: Check if we have the expected structure
        if hasattr(self, 'logger') and self.logger:
            self.logger.debug(f"HTML length: {len(html)} bytes")
            # Check for CAPTCHA or error pages
            if 'captcha' in html.lower() or 'unusual traffic' in html.lower():
                self.logger.warning("Google CAPTCHA or unusual traffic page detected")
            # Save HTML for debugging if needed
            # with open('/tmp/google_search_debug.html', 'w') as f:
            #     f.write(html)
        
        if is_news:
            items = soup.select('div.Gx5Zad')  # Selector for news results (not used,replaced by SoaBEf)
        else:
            items = soup.select('div.tF2Cxc')  # Correct container for regular results
        
        if hasattr(self, 'logger') and self.logger:
            self.logger.debug(f"Found {len(items)} potential result items")
        
        # News search requires different parsing
        if is_news:
            # Use div.SoaBEf as primary container for news items
            news_items = soup.select('div.SoaBEf')
            
            if hasattr(self, 'logger') and self.logger:
                self.logger.debug(f"Found {len(news_items)} news items with div.SoaBEf")
            
            for item in news_items:
                if len(results) >= max_results:
                    break
                
                # Extract title and URL from link
                link = item.select_one('a[href^="https://"]')
                if not link:
                    continue
                
                title = link.get_text(strip=True)
                url = link.get('href', '')
                
                # Skip Google internal links
                if 'google.com' in url or 'gstatic.com' in url:
                    continue
                
                # Extract snippet from nested divs
                snippet = ""
                snippet_elem = item.select_one('div > div > div')
                if snippet_elem:
                    snippet_text = snippet_elem.get_text(strip=True)
                    
                    # Clean up snippet - remove source name and title
                    # The text usually looks like: "SourceNameTitleActual snippet text here..."
                    # Find where the actual snippet starts (after title)
                    if title in snippet_text:
                        # Split on title and take what comes after
                        parts = snippet_text.split(title, 1)
                        if len(parts) > 1:
                            snippet = parts[1].strip()
                            # Remove leading "The arrival of" type phrases if snippet starts with them
                            if snippet:
                                # Remove common prefixes added by link text
                                for prefix in ['The ', 'A ', 'An ']:
                                    if snippet.startswith(prefix) and len(snippet) > len(prefix):
                                        break
                                snippet = snippet[:200]  # Limit length
                    
                    # Fallback: if that didn't work, try to extract meaningful text
                    if not snippet and len(snippet_text) > 50:
                        # Just take text after first 40 chars (likely past source/title)
                        snippet = snippet_text[40:240].strip()
                
                
                # Extract date  
                date_str = ""
                date_elem = item.select_one('div.OSrXXb')
                if date_elem:
                    date_str = date_elem.get_text(strip=True)
                
                item_date = self._parse_date(date_str) if date_str else "Unknown"
                
                # Check date filter
                if date_before and item_date != "Unknown":
                    if not self._validate_time(date_before, item_date):
                        continue
                
                results.append({
                    "title": title,
                    "url": url,
                    "content": snippet,
                    "date": item_date,
                    "source": "google_search"
                })
            
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(f"Parsed {len(results)} news results")
            
            return results
        
        
        # Regular search parsing
        for item in items:
            if len(results) >= max_results:
                break
            
            # Extract title and link from div.yuRUbf
            title_container = item.select_one('div.yuRUbf')
            if not title_container:
                continue
                
            title_elem = title_container.select_one('h3')
            link_elem = title_container.select_one('a')
            
            if not title_elem or not link_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            url = link_elem.get('href', '')
            
            # Extract actual URL from Google redirect
            if url.startswith('/url?q='):
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'q' in params:
                    url = params['q'][0]
            
            if not url.startswith('http'):
                continue
            
            # Extract snippet from div.VwiC3b or div.IsZvec
            snippet = ""
            snippet_elem = item.select_one('div.VwiC3b, div.IsZvec')
            if snippet_elem:
                snippet = snippet_elem.get_text(strip=True)
            
            # Extract date from cite tag (URL breadcrumb)
            date_str = ""
            cite_elem = item.select_one('cite')
            if cite_elem:
                cite_text = cite_elem.get_text(strip=True)
                # Try to extract date from URL pattern
                import re
                date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})|(\d{4})-(\d{2})-(\d{2})', cite_text)
                if date_match:
                    groups = [g for g in date_match.groups() if g]
                    if len(groups) >= 3:
                        # Convert to YYYY-MM-DD format
                        date_str = f"{groups[0]}-{groups[1]}-{groups[2]}"
            
            item_date = date_str if date_str else "Unknown"
            
            if date_before and item_date != "Unknown":
                if not self._validate_time(date_before, item_date):
                    continue
            
            results.append({
                "title": title,
                "url": url,
                "content": snippet,
                "date": item_date,
                "source": "google_search"
            })
        
        if hasattr(self, 'logger') and self.logger:
            self.logger.info(f"Parsed {len(results)} valid results from Google search")
        
        return results

    def _parse_date(self, date_str: str) -> str:
        if not date_str:
            return "Unknown"
        
        date_str = date_str.lower().strip()
        
        if 'ago' in date_str:
            return datetime.now().strftime("%Y-%m-%d")
        
        patterns = [
            r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if 'jan' in pattern or 'feb' in pattern:
                        day, month_str, year = match.groups()
                        months = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                        month = months.get(month_str[:3], 1)
                        return f"{year}-{month:02d}-{int(day):02d}"
                    elif '-' in pattern:
                        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    else:
                        month, day, year = match.groups()
                        return f"{year}-{int(month):02d}-{int(day):02d}"
                except:
                    pass
        
        return "Unknown"

    def _validate_time(self, date_before: str, item_date: str) -> bool:
        try:
            before_dt = datetime.strptime(date_before, "%m/%d/%Y")
            item_dt = datetime.strptime(item_date, "%Y-%m-%d")
            return item_dt <= before_dt
        except:
            return True
