"""
MTG Content Scraper
Scrapes Magic: The Gathering articles and content from major sources
for use in RAG knowledge base.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MTGContentScraper:
    """Scraper for MTG articles and content from various sources."""
    
    def __init__(self, output_dir: str = "scraped_content", delay: float = 1.0):
        """
        Initialize the scraper.
        
        Args:
            output_dir: Directory to save scraped content
            delay: Delay between requests (seconds)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Content sources configuration
        self.sources = {
            'channelfireball': {
                'base_url': 'https://www.channelfireball.com',
                'article_urls': [
                    'https://www.channelfireball.com/articles/',
                    'https://www.channelfireball.com/articles/draft/',
                    'https://www.channelfireball.com/articles/limited/',
                ],
                'selectors': {
                    'article_links': 'a[href*="/articles/"]',
                    'title': 'h1',
                    'content': 'article, .article-content, .post-content',
                    'date': 'time, .date, .published-date',
                    'author': '.author, .byline, [rel="author"]'
                }
            },
            'starcitygames': {
                'base_url': 'https://www.starcitygames.com',
                'article_urls': [
                    'https://www.starcitygames.com/articles/',
                    'https://www.starcitygames.com/articles/limited/',
                ],
                'selectors': {
                    'article_links': 'a[href*="/articles/"]',
                    'title': 'h1, .article-title',
                    'content': 'article, .article-body, .content',
                    'date': 'time, .date',
                    'author': '.author, .byline'
                }
            },
            'mtggoldfish': {
                'base_url': 'https://www.mtggoldfish.com',
                'article_urls': [
                    'https://www.mtggoldfish.com/articles',
                    'https://www.mtggoldfish.com/articles/limited',
                ],
                'selectors': {
                    'article_links': 'a[href*="/articles/"]',
                    'title': 'h1, .article-title',
                    'content': 'article, .article-content, .post-content',
                    'date': 'time, .date',
                    'author': '.author, .byline'
                }
            },
            'tcgplayer': {
                'base_url': 'https://www.tcgplayer.com',
                'article_urls': [
                    'https://www.tcgplayer.com/articles',
                    'https://www.tcgplayer.com/articles/limited',
                ],
                'selectors': {
                    'article_links': 'a[href*="/articles/"]',
                    'title': 'h1',
                    'content': 'article, .article-body',
                    'date': 'time, .date',
                    'author': '.author'
                }
            },
            'reddit': {
                'base_url': 'https://www.reddit.com',
                'article_urls': [
                    'https://www.reddit.com/r/magicTCG/top/?t=all',
                    'https://www.reddit.com/r/lrcast/top/?t=all',
                    'https://www.reddit.com/r/spikes/top/?t=all',
                ],
                'selectors': {
                    'article_links': 'a[data-testid="post-title"]',
                    'title': 'h1',
                    'content': '[data-testid="post-content"], .md',
                    'date': 'time',
                    'author': '[data-testid="post_author"]'
                }
            }
        }
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage."""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.delay)
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract text from a selector."""
        if not soup:
            return None
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None
    
    def extract_all_text(self, soup: BeautifulSoup, selector: str) -> List[str]:
        """Extract all text from matching selectors."""
        if not soup:
            return []
        elements = soup.select(selector)
        return [elem.get_text(strip=True) for elem in elements]
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\(\)\-\'"]', '', text)
        return text.strip()
    
    def scrape_article(self, url: str, source: str) -> Optional[Dict]:
        """Scrape a single article."""
        soup = self.fetch_page(url)
        if not soup:
            return None
        
        config = self.sources[source]
        selectors = config['selectors']
        
        # Extract article data
        title = self.extract_text(soup, selectors['title'])
        if not title:
            # Try alternative title selectors
            title = self.extract_text(soup, 'title')
            if title:
                title = title.split('|')[0].strip()
        
        # Extract content
        content_elements = soup.select(selectors['content'])
        if not content_elements:
            # Fallback: get all paragraph text
            content_elements = soup.select('p')
        
        content_parts = []
        for elem in content_elements:
            text = elem.get_text(strip=True)
            if text and len(text) > 50:  # Filter out short fragments
                content_parts.append(self.clean_text(text))
        
        content = '\n\n'.join(content_parts)
        
        # Extract metadata
        date = self.extract_text(soup, selectors['date'])
        author = self.extract_text(soup, selectors['author'])
        
        if not content or len(content) < 200:  # Skip very short articles
            logger.warning(f"Skipping {url}: content too short")
            return None
        
        return {
            'url': url,
            'title': title or 'Untitled',
            'content': content,
            'source': source,
            'author': author,
            'date': date,
            'scraped_at': datetime.now().isoformat(),
            'word_count': len(content.split())
        }
    
    def find_article_urls(self, source: str, max_pages: int = 10) -> List[str]:
        """Find article URLs from a source."""
        config = self.sources[source]
        article_urls = set()
        
        for base_url in config['article_urls']:
            for page in range(1, max_pages + 1):
                if 'reddit' in source:
                    # Reddit uses different pagination
                    url = base_url
                else:
                    url = f"{base_url}?page={page}" if page > 1 else base_url
                
                soup = self.fetch_page(url)
                if not soup:
                    break
                
                links = soup.select(config['selectors']['article_links'])
                found_new = False
                
                for link in links:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # Make absolute URL
                    full_url = urljoin(config['base_url'], href)
                    
                    # Filter for actual articles
                    if '/articles/' in full_url or '/r/' in full_url:
                        if full_url not in article_urls:
                            article_urls.add(full_url)
                            found_new = True
                
                if not found_new:
                    break
                
                logger.info(f"Found {len(article_urls)} articles from {source} so far")
        
        return list(article_urls)
    
    def scrape_source(self, source: str, max_articles: int = 50) -> List[Dict]:
        """Scrape all articles from a source."""
        if source not in self.sources:
            logger.error(f"Unknown source: {source}")
            return []
        
        logger.info(f"Starting scrape of {source}")
        
        # Find article URLs
        article_urls = self.find_article_urls(source)
        article_urls = article_urls[:max_articles]
        
        logger.info(f"Found {len(article_urls)} articles to scrape")
        
        # Scrape each article
        articles = []
        for i, url in enumerate(article_urls, 1):
            logger.info(f"Scraping article {i}/{len(article_urls)}: {url}")
            article = self.scrape_article(url, source)
            if article:
                articles.append(article)
        
        # Save to file
        output_file = self.output_dir / f"{source}_articles.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(articles)} articles from {source} to {output_file}")
        return articles
    
    def scrape_all_sources(self, max_articles_per_source: int = 50) -> List[Dict]:
        """Scrape all configured sources."""
        all_articles = []
        
        for source in self.sources.keys():
            try:
                articles = self.scrape_source(source, max_articles_per_source)
                all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Error scraping {source}: {e}")
                continue
        
        # Save combined results
        output_file = self.output_dir / "all_articles.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Total articles scraped: {len(all_articles)}")
        return all_articles
    
    def scrape_custom_urls(self, urls: List[str], source_name: str = "custom") -> List[Dict]:
        """Scrape a list of custom URLs."""
        articles = []
        
        for url in urls:
            article = self.scrape_article(url, source_name)
            if article:
                articles.append(article)
        
        return articles


def main():
    """Main function to run the scraper."""
    scraper = MTGContentScraper(output_dir="scraped_content", delay=1.5)
    
    # Scrape all sources
    print("Starting MTG content scraping...")
    articles = scraper.scrape_all_sources(max_articles_per_source=30)
    
    print(f"\nScraping complete! Found {len(articles)} articles.")
    print(f"Articles saved to: {scraper.output_dir}")


if __name__ == "__main__":
    main()

