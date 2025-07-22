import hashlib
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

import feedparser
from bs4 import BeautifulSoup

from ..models.source import SourceItem
from ..utils.logging import get_logger
from ..utils.validation import sanitize_filename


class BaseParser:
    """Base parser class for all source types"""
    
    def __init__(self, source_config: Dict[str, Any]):
        self.source_config = source_config
        self.logger = get_logger(f"sourcerer.sources.parser.{source_config.get('type', 'unknown')}")
        self.timeout = 30
        self.max_content_length = 50000  # 50KB limit per item
    
    async def parse(self, url: str, headers: Dict[str, str] = None) -> List[SourceItem]:
        """Parse source and return list of items"""
        raise NotImplementedError
    
    def _generate_item_id(self, url: str) -> str:
        """Generate unique ID for item based on URL"""
        return hashlib.sha1(url.encode()).hexdigest()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Limit length
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length] + "..."
        
        return text
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc
        except:
            return "unknown"


class RSSParser(BaseParser):
    """RSS/Atom feed parser"""
    
    async def parse(self, url: str, headers: Dict[str, str] = None) -> List[SourceItem]:
        """Parse RSS feed and return items"""
        try:
            self.logger.info(f"Parsing RSS feed: {url}")
            
            # Fetch feed content
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers or {})
                response.raise_for_status()
                feed_content = response.text
            
            # Parse with feedparser
            feed = feedparser.parse(feed_content)
            
            if feed.bozo and feed.bozo_exception:
                self.logger.warning(f"Feed parsing warning: {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries[:self.source_config.get('max_items', 200)]:
                try:
                    item = self._parse_feed_entry(entry, url)
                    if item:
                        items.append(item)
                except Exception as e:
                    self.logger.error(f"Error parsing feed entry: {e}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(items)} items from RSS feed")
            return items
            
        except Exception as e:
            self.logger.error(f"Failed to parse RSS feed {url}: {e}")
            raise
    
    def _parse_feed_entry(self, entry, feed_url: str) -> Optional[SourceItem]:
        """Parse individual feed entry"""
        try:
            # Get entry URL
            entry_url = getattr(entry, 'link', '')
            if not entry_url:
                return None
            
            # Make URL absolute if needed
            if entry_url.startswith('/'):
                entry_url = urljoin(feed_url, entry_url)
            
            # Extract published date
            published_at = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    import time
                    published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                except:
                    pass
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                try:
                    import time
                    published_at = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                except:
                    pass
            
            # Extract content
            content = ""
            summary = ""
            
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if isinstance(entry.content, list) else str(entry.content)
            elif hasattr(entry, 'description'):
                content = entry.description
            
            if hasattr(entry, 'summary'):
                summary = entry.summary
            
            # Clean HTML from content
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = self._clean_text(soup.get_text())
            
            if summary:
                soup = BeautifulSoup(summary, 'html.parser')
                summary = self._clean_text(soup.get_text())
            
            # Extract tags
            tags = []
            if hasattr(entry, 'tags'):
                tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            
            # Extract author
            author = ""
            if hasattr(entry, 'author'):
                author = entry.author
            elif hasattr(entry, 'authors') and entry.authors:
                author = entry.authors[0].name if hasattr(entry.authors[0], 'name') else str(entry.authors[0])
            
            return SourceItem(
                id=self._generate_item_id(entry_url),
                title=self._clean_text(getattr(entry, 'title', 'Untitled')),
                url=entry_url,
                published_at=published_at,
                summary=summary[:500] if summary else None,  # Limit summary length
                content=content,
                author=author,
                tags=tags,
                raw={
                    'source_type': 'rss',
                    'feed_url': feed_url,
                    'entry_id': getattr(entry, 'id', ''),
                    'domain': self._extract_domain(entry_url)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing RSS entry: {e}")
            return None


class HTMLParser(BaseParser):
    """HTML page parser using heuristics and OpenGraph"""
    
    async def parse(self, url: str, headers: Dict[str, str] = None) -> List[SourceItem]:
        """Parse HTML page and return items"""
        try:
            self.logger.info(f"Parsing HTML page: {url}")
            
            # Fetch page content
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=headers or {})
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type.lower():
                    raise ValueError(f"Not an HTML page: {content_type}")
                
                html_content = response.text
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract page information
            item = self._parse_html_page(soup, url)
            
            if item:
                self.logger.info(f"Successfully parsed HTML page: {item.title}")
                return [item]
            else:
                self.logger.warning(f"Failed to extract meaningful content from: {url}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to parse HTML page {url}: {e}")
            raise
    
    def _parse_html_page(self, soup: BeautifulSoup, url: str) -> Optional[SourceItem]:
        """Extract content from HTML page"""
        try:
            # Extract title
            title = ""
            
            # Try OpenGraph title
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content']
            
            # Try Twitter title
            if not title:
                twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
                if twitter_title and twitter_title.get('content'):
                    title = twitter_title['content']
            
            # Try regular title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text()
            
            # Try h1 tag
            if not title:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text()
            
            title = self._clean_text(title) or "Untitled"
            
            # Extract description/summary
            summary = ""
            
            # Try OpenGraph description
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                summary = og_desc['content']
            
            # Try meta description
            if not summary:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    summary = meta_desc['content']
            
            # Try Twitter description
            if not summary:
                twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
                if twitter_desc and twitter_desc.get('content'):
                    summary = twitter_desc['content']
            
            summary = self._clean_text(summary)
            
            # Extract main content
            content = self._extract_main_content(soup)
            
            # Extract author
            author = ""
            
            # Try various author meta tags
            author_selectors = [
                ('meta', {'name': 'author'}),
                ('meta', {'property': 'article:author'}),
                ('meta', {'name': 'twitter:creator'}),
                ('[rel="author"]', {}),
                ('.author', {}),
                ('.byline', {}),
            ]
            
            for selector, attrs in author_selectors:
                if author:
                    break
                    
                if selector.startswith('[') or selector.startswith('.'):
                    elements = soup.select(selector)
                else:
                    elements = soup.find_all(selector, attrs)
                
                for element in elements:
                    if element.get('content'):
                        author = element['content']
                        break
                    elif element.get_text():
                        author = element.get_text()
                        break
            
            author = self._clean_text(author)
            
            # Extract tags/keywords
            tags = []
            
            # Try meta keywords
            keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
            if keywords_meta and keywords_meta.get('content'):
                keywords = keywords_meta['content']
                tags = [tag.strip() for tag in keywords.split(',') if tag.strip()]
            
            # Try article tags
            article_tags = soup.find('meta', property='article:tag')
            if article_tags and article_tags.get('content'):
                tags.extend([tag.strip() for tag in article_tags['content'].split(',') if tag.strip()])
            
            # Extract published date
            published_at = datetime.now()
            
            # Try various date selectors
            date_selectors = [
                ('meta', {'property': 'article:published_time'}),
                ('meta', {'name': 'date'}),
                ('meta', {'name': 'publish-date'}),
                ('time', {'datetime': True}),
                ('.date', {}),
                ('.published', {}),
            ]
            
            for selector, attrs in date_selectors:
                try:
                    if selector == 'time':
                        time_elem = soup.find('time', attrs=lambda x: x and 'datetime' in x)
                        if time_elem and time_elem.get('datetime'):
                            from dateutil import parser
                            published_at = parser.parse(time_elem['datetime'])
                            break
                    else:
                        elem = soup.find(selector, attrs)
                        if elem:
                            date_str = elem.get('content') or elem.get_text()
                            if date_str:
                                from dateutil import parser
                                published_at = parser.parse(date_str)
                                break
                except:
                    continue
            
            return SourceItem(
                id=self._generate_item_id(url),
                title=title,
                url=url,
                published_at=published_at,
                summary=summary[:500] if summary else None,
                content=content,
                author=author,
                tags=tags[:10],  # Limit tags
                raw={
                    'source_type': 'html',
                    'domain': self._extract_domain(url),
                    'content_length': len(content),
                    'has_og_data': bool(og_title or og_desc)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing HTML content: {e}")
            return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML using heuristics"""
        content_parts = []
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
            element.decompose()
        
        # Try to find main content areas
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.content',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.story-body',
            '#content',
            '#main-content',
            '.main-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                main_content = elements[0]
                break
        
        if main_content:
            # Extract text from main content area
            text = main_content.get_text(separator=' ', strip=True)
            content_parts.append(text)
        else:
            # Fallback: extract from common paragraph containers
            for tag in ['p', 'div', 'section']:
                elements = soup.find_all(tag)
                for element in elements:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 50:  # Only consider substantial text blocks
                        content_parts.append(text)
        
        # Combine and clean content
        full_content = ' '.join(content_parts)
        return self._clean_text(full_content)