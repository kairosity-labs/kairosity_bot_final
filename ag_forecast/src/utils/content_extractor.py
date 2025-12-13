import asyncio
import hashlib
from typing import List, Dict, Any, Set
from urllib.parse import urlparse
from patchright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from .html_extractor import HTMLContentExtractor
from bs4 import BeautifulSoup


class ContentExtractor:
    """Enhanced content extractor with anti-detection, quality validation, and metadata extraction."""
    
    # Class-level semaphore for rate limiting
    _semaphore = asyncio.Semaphore(3)  # Max 3 concurrent scrapes
    _seen_hashes: Set[str] = set()  # For deduplication
    
    def __init__(self):
        self.html_extractor = HTMLContentExtractor()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]

    async def extract(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract content from URLs with rate limiting."""
        results = {}
        tasks = [asyncio.create_task(self._fetch_url_with_retry(url, idx % len(self.user_agents))) 
                for idx, url in enumerate(urls)]
        
        done, pending = await asyncio.wait(tasks, timeout=90)  # Increased timeout
        
        for task in done:
            try:
                result = task.result()
                results[result['url']] = result
            except Exception:
                pass
        
        for task in pending:
            task.cancel()
            try:
                url = urls[tasks.index(task)]
                results[url] = {
                    'url': url,
                    'domain': urlparse(url).netloc,
                    'content': None,
                    'error': 'Operation timed out',
                    'success': False
                }
            except Exception:
                pass
        
        return results

    async def _fetch_url_with_retry(self, url: str, user_agent_idx: int) -> Dict[str, Any]:
        """Fetch URL with retry logic and exponential backoff."""
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                result = await self._fetch_url(url, user_agent_idx, attempt)
                
                # Check for blockers
                if result.get('success') and result.get('raw_html'):
                    blockers = self._detect_blockers(result['raw_html'])
                    
                    if blockers['captcha'] or blockers['robot_check']:
                        if attempt < max_retries - 1:
                            # Retry with delay
                            await asyncio.sleep(base_delay * (2 ** attempt))
                            continue
                        else:
                            result['error'] = 'CAPTCHA/bot detection persists'
                            result['success'] = False
                
                return result
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        'url': url,
                        'domain': urlparse(url).netloc,
                        'content': None,
                        'error': f'All retries failed: {str(e)}',
                        'success': False
                    }
                await asyncio.sleep(base_delay * (2 ** attempt))
        
        return {
            'url': url,
            'domain': urlparse(url).netloc,
            'content': None,
            'error': 'Max retries exceeded',
            'success': False
        }

    async def _fetch_url(self, url: str, user_agent_idx: int, attempt: int = 0) -> Dict[str, Any]:
        """Fetch single URL with full anti-detection."""
        async with self._semaphore:
            # Rate limiting delay
            if attempt == 0:
                await asyncio.sleep(2)
            
            try:
                async with async_playwright() as p:
                    # Launch with anti-detection
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
                        user_agent=self.user_agents[user_agent_idx],
                        viewport={"width": 1920, "height": 1080},
                        locale='en-US',
                        timezone_id='America/New_York',
                        extra_http_headers={
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'DNT': '1',
                            'Connection': 'keep-alive'
                        }
                    )
                    
                    page = await context.new_page()
                    
                    # Navigator overrides
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3]
                        });
                    """)
                    
                    # Adaptive timeout
                    timeout = self._get_timeout_for_domain(url)
                    page.set_default_navigation_timeout(timeout * 1000)
                    
                    try:
                        await page.goto(url, wait_until="domcontentloaded")
                        
                        # Cookie consent handling
                        await self._handle_cookie_consent(page)
                        
                        # Smart JS wait
                        await self._wait_for_content(page)
                        
                        raw_html = await page.content()
                    except PlaywrightTimeoutError:
                        raw_html = await page.content()
                    finally:
                        await browser.close()

                    # Validate HTML length
                    if not raw_html or len(raw_html.strip()) < 1400:
                        return {
                            'url': url,
                            'domain': urlparse(url).netloc,
                            'content': None,
                            'error': 'Empty or very short HTML received',
                            'success': False
                        }

                    # Extract content
                    processed_content = self.html_extractor.extract(url, raw_html)
                    
                    if not processed_content:
                        return {
                            'url': url,
                            'domain': urlparse(url).netloc,
                            'content': None,
                            'error': 'Content extraction failed',
                            'success': False
                        }

                    # Quality validation
                    quality = self._validate_content_quality(processed_content, raw_html)
                    
                    if not quality['has_meaningful_text']:
                        return {
                            'url': url,
                            'domain': urlparse(url).netloc,
                            'content': None,
                            'error': f"Low quality content: {quality}",
                            'success': False,
                            'quality_score': quality.get('quality_score', 0)
                        }
                    
                    # Deduplication check
                    if self._is_duplicate(processed_content):
                        return {
                            'url': url,
                            'domain': urlparse(url).netloc,
                            'content': None,
                            'error': 'Duplicate content',
                            'success': False
                        }
                    
                    # Extract metadata
                    metadata = self._extract_metadata(raw_html, url)

                    return {
                        'url': url,
                        'domain': urlparse(url).netloc,
                        'content': processed_content,
                        'success': True,
                        'raw_html': raw_html,  # Keep for blocker detection
                        'metadata': metadata,
                        'quality_score': quality.get('quality_score', 80)
                    }
                    
            except asyncio.TimeoutError:
                return {
                    'url': url,
                    'domain': urlparse(url).netloc,
                    'content': None,
                    'error': 'Request timed out',
                    'success': False
                }
            except Exception as e:
                return {
                    'url': url,
                    'domain': urlparse(url).netloc,
                    'content': None,
                    'error': str(e),
                    'success': False
                }

    def _detect_blockers(self, html: str) -> dict:
        """Detect CAPTCHAs, paywalls, error pages."""
        html_lower = html.lower()
        return {
            'captcha': 'captcha' in html_lower or 'recaptcha' in html_lower,
            'paywall': 'paywall' in html_lower or ('subscribe' in html_lower and 'unlock' in html_lower),
            'error_page': '404' in html or '403' in html or 'access denied' in html_lower,
            'robot_check': 'robot' in html_lower or 'unusual traffic' in html_lower
        }

    def _validate_content_quality(self, content: str, html: str) -> dict:
        """Multi-dimensional quality assessment."""
        words = content.split()
        word_count = len(words)
        
        return {
            'word_count': word_count,
            'has_meaningful_text': word_count >= 150,  # Increased threshold
            'is_navigation_page': content.count('©') > 5,
            'quality_score': min(100, max(0, (word_count / 500) * 100))  # Simple scoring
        }

    def _is_duplicate(self, content: str) -> bool:
        """Check if content is duplicate."""
        content_hash = hashlib.md5(content[:500].encode()).hexdigest()
        if content_hash in ContentExtractor._seen_hashes:
            return True
        ContentExtractor._seen_hashes.add(content_hash)
        return False

    def _extract_metadata(self, html: str, url: str) -> dict:
        """Extract rich metadata from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Author
            author = None
            author_meta = soup.find('meta', attrs={'name': 'author'}) or soup.find('meta', attrs={'property': 'article:author'})
            if author_meta:
                author = author_meta.get('content')
            
            # Publish date
            publish_date = None
            date_meta = soup.find('meta', attrs={'property': 'article:published_time'}) or soup.find('meta', attrs={'name': 'publish_date'})
            if date_meta:
                publish_date = date_meta.get('content')
            
            # Description
            description = None
            desc_meta = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if desc_meta:
                description = desc_meta.get('content')
            
            return {
                'author': author,
                'publish_date': publish_date,
                'description': description
            }
        except Exception:
            return {}

    async def _handle_cookie_consent(self, page) -> bool:
        """Auto-dismiss cookie consent banners."""
        consent_selectors = [
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'button:has-text("Agree")',
            'button:has-text("Accept all")',
            '#onetrust-accept-btn-handler',
            '.cookie-accept',
            '[aria-label*="Accept"]'
        ]
        
        for selector in consent_selectors:
            try:
                await page.click(selector, timeout=2000)
                await asyncio.sleep(0.5)
                return True
            except:
                continue
        return False

    async def _wait_for_content(self, page):
        """Adaptive wait for JS-heavy sites."""
        try:
            # Detect if SPA
            is_spa = await page.evaluate('''
                () => {
                    return !!(window.React || window.Vue || window.Angular || 
                             document.querySelector('[data-reactroot]') ||
                             document.querySelector('[data-react-helmet]'));
                }
            ''')
            
            if is_spa:
                await asyncio.sleep(2)
                try:
                    await page.wait_for_load_state('networkidle', timeout=5000)
                except:
                    pass
            else:
                await asyncio.sleep(1)
        except:
            await asyncio.sleep(1.5)

    def _get_timeout_for_domain(self, url: str) -> int:
        """Domain-specific timeouts."""
        domain = urlparse(url).netloc
        
        slow_domains = ['nytimes.com', 'wsj.com', 'ft.com', 'economist.com']
        fast_domains = ['reuters.com', 'apnews.com', 'bbc.com', 'bloomberg.com']
        
        if any(d in domain for d in slow_domains):
            return 30
        elif any(d in domain for d in fast_domains):
            return 15
        else:
            return 20
