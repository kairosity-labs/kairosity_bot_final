import re
import html as html_lib
from typing import Optional, Dict
from bs4 import BeautifulSoup, Tag
from trafilatura import extract as trafilatura_extract
from trafilatura.settings import use_config
from readability import Document
from boilerpy3 import extractors


class HTMLContentExtractor:
    def __init__(self, site_configs: Optional[Dict[str, dict]] = None):
        self.extractor = extractors.ArticleExtractor()
        self.site_configs = site_configs or self._default_site_configs()
        self.blacklist_patterns = self._default_blacklist_patterns()
        self.removal_keywords = [
            'embeddable', 'subscribe', 'subscription', 'newsletter', 'sign up',
            'share this', 'follow us', 'copyright', 'all rights reserved',
            'read more', 'more on this', 'see more', 'gallery', 'slideshow',
            'click here', 'download', 'register', 'privacy policy', 'terms of service',
            'thanks for sharing', 'photo:', 'image:', 'published', 'updated'
        ]

    def _default_site_configs(self) -> Dict[str, dict]:
        return {
            'nytimes.com': {
                'selectors': ['article#story', 'div.StoryBodyCompanionColumn'],
                'remove_selectors': ['div.ad', 'div.comments', 'div.toolbar']
            },
            'reuters.com': {
                'selectors': ['article.article-body', 'div[data-testid="Body"]'],
                'remove_selectors': ['div.article-header', 'div.article-share']
            },
            'washingtonpost.com': {
                'selectors': ['div.article-body', 'article.main-content'],
                'remove_selectors': ['div.interstitial', 'div.newsletter-inline-unit']
            },
            'economist.com': {
                'selectors': ['article.article__body', 'div.article__lead', 'div.article__content'],
                'remove_selectors': ['div.advert', 'div.article__footnote', 'div.share-links']
            },
            'baltimoresun.com': {
                'selectors': ['div.body-copy', 'article.story'],
                'remove_selectors': ['div.map-container', 'div#president', 'div#senate']
            },
            'bloomberg.com': {
                'selectors': ['div.body-content', 'div.body-copy', 'article.article-body'],
                'remove_selectors': ['div.paywall', 'div.newsletter-signup', 'div.related-articles']
            },
            'channelnewsasia.com': {
                'selectors': ['div.article-content', 'div.article-body', 'article'],
                'remove_selectors': ['div.advertisement', 'div.teaser', 'div.partner-recommendations']
            },
            'cna.com.sg': {
                'selectors': ['div.article-content', 'div.article-body', 'article'],
                'remove_selectors': ['div.advertisement', 'div.teaser', 'div.partner-recommendations']
            },
            'techcrunch.com': {
                'selectors': ['div.article-content', 'p.wp-block-paragraph', 'ul.wp-block-list'],
                'remove_selectors': ['div[class*="ad"]', 'div[class*="related"]', 'aside', 'nav']
            }
        }

    def _default_blacklist_patterns(self):
        return [
            r'Advertisement\s*', r'ADVERTISEMENT\s*', r'Recommended\s*',
            r'Subscribe.*?(?=\n|$)', r'Sign up for.*?(?=\n|$)', r'Newsletter.*?(?=\n|$)',
            r'©\s*\d{4}.*?(?=\n|$)', r'All rights reserved.*?(?=\n|$)',
            r'Follow us on.*?(?=\n|$)', r'Share this article.*?(?=\n|$)',
            r'Read more:.*?(?=\n|$)', r'\[\s*\d+\s*chars\s*\]', r'^\s*https?://[^\s]+$'
        ]

    def extract(self, url: str, html_content: str) -> Optional[str]:
        if not html_content or len(html_content.strip()) < 100:
            return None

        html_content = self._preprocess_html(html_content)
        metadata = self._extract_metadata(html_content, url)
        
        candidates = []
        
        site_specific = self._extract_with_selectors(html_content, url)
        if site_specific and len(site_specific.strip()) > 500:
            candidates.append((site_specific, 1.2, 'site-specific'))

        trafilatura_result = self._extract_trafilatura(html_content)
        if trafilatura_result:
            candidates.append((trafilatura_result, 1.0, 'trafilatura'))

        readability_result = self._extract_readability(html_content)
        if readability_result:
            candidates.append((readability_result, 0.9, 'readability'))

        boilerpy_result = self._extract_boilerpy(html_content)
        if boilerpy_result:
            candidates.append((boilerpy_result, 0.8, 'boilerpy'))

        if candidates:
            scored = [(c, w * self._calculate_quality(c) * min(len(c) / 5000, 1.0), l) 
                     for c, w, l in candidates]
            best_content, _, _ = max(scored, key=lambda x: x[1])
            return self._format_with_metadata(self._clean_content(best_content), metadata)

        soup = BeautifulSoup(html_content, 'html.parser')
        guessed_div = self._guess_main_content_div(soup)
        if guessed_div:
            text = guessed_div.get_text(separator=" ", strip=True)
            if text:
                return self._format_with_metadata(self._clean_content(text), metadata)

        fallback = self._fallback_extract_paragraphs(soup)
        if fallback:
            return self._format_with_metadata(self._clean_content(fallback), metadata)

        return None

    def _preprocess_html(self, html_content: str) -> str:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for tag in soup.find_all(['script', 'style', 'svg', 'noscript']):
                tag.decompose()
            for tag in soup.find_all(style=re.compile(r'display:\s*none|visibility:\s*hidden')):
                tag.decompose()
            for div in soup.find_all('div', {'id': re.compile(r'footer|banner|sidebar|comment')}):
                div.decompose()
            return str(soup)
        except Exception:
            return html_content

    def _extract_with_selectors(self, html_content: str, url: str) -> Optional[str]:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        config = next((self.site_configs[d] for d in self.site_configs if d in domain), {})
        
        selectors = config.get("selectors", [
            'article', '.article', '.article-body', '.content', '.entry-content',
            'div[itemprop="articleBody"]', '.story-body', '.post-content', 'main'
        ])
        remove_selectors = config.get("remove_selectors", [])

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for selector in remove_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            for tag in soup.find_all(['aside', 'nav', 'footer']):
                tag.decompose()
            
            for tag in soup.find_all(class_=re.compile(r'(ad-|banner|promo|sponsored)')):
                tag.decompose()

            content_parts = []
            for selector in selectors:
                for element in soup.select(selector):
                    self._clean_element(element)
                    paragraphs = self._extract_paragraphs_from_element(element)
                    if paragraphs:
                        content_parts.append('\n\n'.join(paragraphs))

            if not content_parts:
                paragraphs = [p.get_text(separator=" ", strip=True) 
                            for p in soup.find_all(['p']) 
                            if len(p.get_text(strip=True)) > 20 and not self._is_boilerplate(p.get_text(strip=True))]
                return '\n\n'.join(paragraphs) if paragraphs else None

            return '\n\n'.join(content_parts)
        except Exception:
            return None

    def _extract_paragraphs_from_element(self, element) -> list:
        paragraphs = []
        children = list(element.children)
        i = 0
        while i < len(children):
            child = children[i]
            if not isinstance(child, Tag):
                i += 1
                continue

            text = child.get_text(separator=" ", strip=True)
            if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and text:
                merged = [text]
                j = i + 1
                while j < len(children):
                    next_child = children[j]
                    if isinstance(next_child, Tag) and next_child.name in ['p', 'div', 'ul', 'ol']:
                        para = next_child.get_text(separator=" ", strip=True)
                        if para and len(para) > 30 and not self._is_boilerplate(para):
                            merged.append(para)
                            i = j
                            break
                    j += 1
                paragraphs.append("\n".join(merged))
            elif child.name in ['p', 'li'] and text and len(text) > 40 and not self._is_boilerplate(text):
                paragraphs.append(text)
            i += 1
        return paragraphs

    def _clean_element(self, element):
        for tag in element.find_all(['script', 'style', 'button', 'form', 'input', 'iframe']):
            tag.decompose()
        for tag in element.find_all(class_=re.compile(r'share|social|comment|related|promo|ad|subscribe|newsletter')):
            tag.decompose()
        for p in element.find_all('p'):
            if not p.get_text(separator=" ", strip=True) or len(p.get_text(separator=" ", strip=True)) < 5:
                p.decompose()

    def _is_boilerplate(self, text: str) -> bool:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in self.removal_keywords):
            return True
        if len(text) < 20 and (text.isupper() or text.count('.') == 0 or 
                              re.search(r'^\d+:\d+$', text) or re.search(r'^[^\w]*https?://', text)):
            return True
        return False

    def _extract_trafilatura(self, html_content: str) -> Optional[str]:
        try:
            config = use_config()
            if not config.has_section("EXTRACTION"):
                config.add_section("EXTRACTION")
            config.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
            config.set("EXTRACTION", "favor_precision", "true")
            result = trafilatura_extract(html_content, config=config)
            return result if result and len(result) > 300 else None
        except Exception:
            return None

    def _extract_readability(self, html_content: str) -> Optional[str]:
        try:
            doc = Document(html_content)
            soup = BeautifulSoup(doc.summary(), 'html.parser')
            
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            for tag in soup.find_all(class_=re.compile(r'ads|share|comment|social|promo|related')):
                tag.decompose()

            paragraphs = []
            for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = element.get_text(separator=" ", strip=True)
                if text and len(text) > 15 and not self._is_boilerplate(text):
                    paragraphs.append(text)

            if len(''.join(paragraphs)) < 1000:
                for div in soup.find_all('div'):
                    if not div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                        text = div.get_text(separator=" ", strip=True)
                        if text and len(text) > 50 and not self._is_boilerplate(text):
                            for section in re.split(r'(?<=[.!?])\s+', text):
                                if len(section) > 40:
                                    paragraphs.append(section)

            return '\n\n'.join(paragraphs) if paragraphs else None
        except Exception:
            return None

    def _extract_boilerpy(self, html_content: str) -> Optional[str]:
        try:
            content = self.extractor.get_content(html_content)
            if content:
                lines = content.split('\n')
                filtered = [line for line in lines if len(line) > 20 and not self._is_boilerplate(line)]
                return '\n\n'.join(filtered) if filtered else None
            return None
        except Exception:
            return None

    def _guess_main_content_div(self, soup: BeautifulSoup) -> Optional[Tag]:
        candidates = []
        for div in soup.find_all('div'):
            class_attr = ' '.join(div.get('class', []))
            if any(kw in class_attr for kw in ['footer', 'nav', 'sidebar', 'header', 'promo', 'share']):
                continue
            text = div.get_text(separator=' ', strip=True)
            p_count = len(div.find_all('p'))
            if len(text) > 500 and p_count >= 3:
                candidates.append((div, len(text)))
        return sorted(candidates, key=lambda x: x[1], reverse=True)[0][0] if candidates else None

    def _fallback_extract_paragraphs(self, soup: BeautifulSoup) -> Optional[str]:
        paragraphs = []
        for tag in soup.find_all(['p', 'li', 'h2', 'h3']):
            text = tag.get_text(separator=" ", strip=True)
            if text and len(text) > 40 and not self._is_boilerplate(text):
                paragraphs.append(text)
        return '\n\n'.join(paragraphs) if paragraphs else None

    def _calculate_quality(self, content: str) -> float:
        if not content:
            return 0.0
        
        lines = content.splitlines()
        avg_line_length = sum(len(line) for line in lines) / max(1, len(lines))
        sentence_count = content.count('.') + content.count('!') + content.count('?')
        word_count = len(content.split())
        
        quality_score = min(1.0, (sentence_count / max(1, word_count / 20)) * 
                          (min(avg_line_length, 100) / 100))
        
        alphanumeric_ratio = sum(c.isalnum() or c.isspace() for c in content) / max(1, len(content))
        quality_score *= max(0.5, alphanumeric_ratio)
        
        uppercase_ratio = sum(c.isupper() for c in content) / max(1, len(content) - content.count(' '))
        if uppercase_ratio > 0.3:
            quality_score *= 0.8
        
        return quality_score

    def _clean_content(self, content: str) -> str:
        if not content:
            return ""

        content = html_lib.unescape(content)
        content = re.sub(r'[\x00-\x1F\x7F]', ' ', content)
        content = re.sub(r'\s+([.,;!?])', r'\1', content)
        content = re.sub(r'([.,;!?])(?=\w)', r'\1 ', content)
        content = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', content)
        content = re.sub(r'(?<=[a-zA-Z])(?=\d)', ' ', content)
        content = re.sub(r'(?<=\d)(?=[a-zA-Z])', ' ', content)
        content = re.sub(r' {2,}', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

        for pattern in self.blacklist_patterns:
            content = re.sub(pattern, ' ', content, flags=re.IGNORECASE | re.MULTILINE)

        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()

    def _extract_metadata(self, html_content: str, url: str) -> Dict:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            metadata = {}
            
            for meta in soup.find_all('meta'):
                if meta.get('property') in ['og:title', 'twitter:title'] and meta.get('content'):
                    metadata['title'] = meta.get('content').strip()
                    break
            if 'title' not in metadata:
                h1 = soup.find('h1')
                if h1:
                    metadata['title'] = h1.get_text(separator=" ", strip=True)
                else:
                    title_tag = soup.find('title')
                    if title_tag:
                        metadata['title'] = title_tag.get_text(separator=" ", strip=True)

            for meta in soup.find_all('meta'):
                if meta.get('name') in ['author', 'article:author'] and meta.get('content'):
                    metadata['author'] = meta.get('content').strip()
                    break

            for meta in soup.find_all('meta'):
                if meta.get('property') in ['article:published_time', 'og:published_time'] and meta.get('content'):
                    metadata['date'] = meta.get('content').strip()
                    break
            if 'date' not in metadata:
                time_elem = soup.find('time')
                if time_elem and time_elem.get('datetime'):
                    metadata['date'] = time_elem.get('datetime')

            for meta in soup.find_all('meta'):
                if meta.get('property') == 'og:site_name' and meta.get('content'):
                    metadata['source'] = meta.get('content').strip()
                    break
            if 'source' not in metadata:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.replace('www.', '')
                metadata['source'] = re.sub(r'\.(com|org|net|gov|edu|io)$', '', domain).capitalize()

            return {k: v for k, v in metadata.items() if v}
        except Exception:
            return {}

    def _format_with_metadata(self, content: str, metadata: Dict) -> str:
        if not content:
            return ""
        
        has_title = False
        if 'title' in metadata and metadata['title']:
            title_start = metadata['title'][:30].lower()
            content_start = content[:100].lower()
            has_title = title_start in content_start

        header_parts = []
        if 'title' in metadata and metadata['title'] and not has_title:
            header_parts.append(f"# {metadata['title']}")

        meta_parts = []
        if 'source' in metadata and metadata['source']:
            meta_parts.append(f"Source: {metadata['source']}")
        if 'date' in metadata and metadata['date']:
            try:
                from datetime import datetime
                import dateutil.parser
                parsed_date = dateutil.parser.parse(metadata['date'])
                meta_parts.append(f"Date: {parsed_date.strftime('%B %d, %Y')}")
            except:
                meta_parts.append(f"Date: {metadata['date']}")
        if 'author' in metadata and metadata['author']:
            meta_parts.append(f"Author: {metadata['author']}")

        if meta_parts:
            header_parts.append("\n".join(meta_parts))

        if header_parts:
            return "\n\n".join(header_parts + [content])
        
        return content
