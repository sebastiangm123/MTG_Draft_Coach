"""
Scraping Agent
Downloads articles and posts from discovered locations.
Saves content to a folder for processing.
"""

import csv
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ScrapingAgent:
    """Agent that scrapes content from discovered locations."""
    
    def __init__(self, locations_csv: str, output_dir: str = "scraped_knowledge"):
        """
        Initialize scraping agent.
        
        Args:
            locations_csv: CSV file with discovered locations
            output_dir: Directory to save scraped content
        """
        self.locations_csv = Path(locations_csv)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.scraped_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        
        # Content selectors for different sites
        self.site_selectors = {
            'channelfireball.com': {
                'title': 'h1, .article-title',
                'content': 'article, .article-content, .post-content',
                'author': '.author, .byline',
                'date': 'time, .date'
            },
            'starcitygames.com': {
                'title': 'h1, .article-title',
                'content': 'article, .article-body, .content',
                'author': '.author, .byline',
                'date': 'time, .date'
            },
            'mtggoldfish.com': {
                'title': 'h1, .article-title',
                'content': 'article, .article-content',
                'author': '.author',
                'date': 'time, .date'
            },
            'tcgplayer.com': {
                'title': 'h1',
                'content': 'article, .article-body',
                'author': '.author',
                'date': 'time, .date'
            },
            'reddit.com': {
                'title': '[data-testid="post-title"]',
                'content': '[data-testid="post-content"], .md',
                'author': '[data-testid="post_author"]',
                'date': 'time'
            },
            'youtube.com': {
                'title': 'h1.ytd-watch-metadata, .watch-title',
                'content': '#description, .ytd-expander',
                'author': '.ytd-channel-name a',
                'date': '.date'
            },
            'default': {
                'title': 'h1, title',
                'content': 'article, main, .content, .post-content',
                'author': '.author, [rel="author"]',
                'date': 'time, .date'
            }
        }
    
    def get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc.replace('www.', '')
        except:
            return 'unknown'
    
    def get_selectors(self, url: str) -> Dict:
        """Get content selectors for a URL."""
        domain = self.get_domain(url)
        
        for site_domain, selectors in self.site_selectors.items():
            if site_domain in domain:
                return selectors
        
        return self.site_selectors['default']
    
    def clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        return text.strip()
    
    def extract_content(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Extract text from a selector."""
        if not soup:
            return None
        
        elements = soup.select(selector)
        if not elements:
            return None
        
        texts = [elem.get_text(strip=True) for elem in elements]
        combined = ' '.join(texts)
        return self.clean_text(combined) if combined else None
    
    def scrape_url(self, url: str, source: str = '') -> Optional[Dict]:
        """Scrape content from a URL."""
        try:
            logger.debug(f"Scraping: {url}")
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                logger.debug(f"Skipping non-HTML content: {url}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            selectors = self.get_selectors(url)
            
            # Extract content
            title = self.extract_content(soup, selectors['title'])
            if not title:
                # Fallback to page title
                title_tag = soup.find('title')
                title = title_tag.get_text(strip=True) if title_tag else 'Untitled'
            
            content = self.extract_content(soup, selectors['content'])
            if not content:
                # Fallback: get all paragraph text
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                content = self.clean_text(content)
            
            if not content or len(content) < 200:
                logger.debug(f"Content too short: {url}")
                return None
            
            author = self.extract_content(soup, selectors['author'])
            date = self.extract_content(soup, selectors['date'])
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'author': author or '',
                'date': date or '',
                'source': source or self.get_domain(url),
                'scraped_at': datetime.now().isoformat(),
                'word_count': len(content.split()),
                'char_count': len(content)
            }
        
        except requests.exceptions.RequestException as e:
            logger.debug(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
            return None
    
    def save_article(self, article: Dict):
        """Save scraped article to file."""
        # Create safe filename from URL
        url_hash = abs(hash(article['url'])) % (10 ** 10)
        safe_title = re.sub(r'[^\w\s-]', '', article['title'])[:50]
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{safe_title}_{url_hash}.json"
        
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(article, f, indent=2, ensure_ascii=False)
    
    def load_locations(self) -> List[Dict]:
        """Load locations from CSV."""
        if not self.locations_csv.exists():
            logger.error(f"Locations CSV not found: {self.locations_csv}")
            return []
        
        locations = []
        with open(self.locations_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('status', 'pending') == 'pending':
                    locations.append(row)
        
        logger.info(f"Loaded {len(locations)} pending locations from {self.locations_csv}")
        return locations
    
    def update_location_status(self, url: str, status: str):
        """Update location status in CSV."""
        # Read all rows
        rows = []
        with open(self.locations_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Update matching row
        for row in rows:
            if row.get('url') == url:
                row['status'] = status
                break
        
        # Write back
        if rows:
            with open(self.locations_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = list(rows[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
    
    def run(self, delay: float = 1.0, max_articles: Optional[int] = None):
        """
        Run scraping agent.
        
        Args:
            delay: Delay between requests (seconds)
            max_articles: Maximum articles to scrape (None = all)
        """
        logger.info("=" * 60)
        logger.info("Starting Scraping Agent")
        logger.info("=" * 60)
        logger.info(f"Locations CSV: {self.locations_csv}")
        logger.info(f"Output directory: {self.output_dir}")
        
        locations = self.load_locations()
        
        if not locations:
            logger.warning("No locations to scrape")
            return
        
        if max_articles:
            locations = locations[:max_articles]
        
        logger.info(f"Scraping {len(locations)} locations...")
        
        for i, location in enumerate(locations, 1):
            url = location.get('url', '')
            if not url:
                continue
            
            logger.info(f"[{i}/{len(locations)}] Scraping: {url}")
            
            article = self.scrape_url(url, location.get('source', ''))
            
            if article:
                self.save_article(article)
                self.scraped_count += 1
                self.update_location_status(url, 'scraped')
                logger.info(f"  ✓ Saved: {article['title'][:60]}... ({article['word_count']} words)")
            else:
                self.failed_count += 1
                self.update_location_status(url, 'failed')
                logger.warning(f"  ✗ Failed to scrape")
            
            # Rate limiting
            time.sleep(delay)
            
            # Progress update
            if i % 10 == 0:
                logger.info(f"Progress: {self.scraped_count} scraped, {self.failed_count} failed")
        
        # Create summary
        summary = {
            'total_locations': len(locations),
            'scraped': self.scraped_count,
            'failed': self.failed_count,
            'skipped': self.skipped_count,
            'output_dir': str(self.output_dir),
            'completed_at': datetime.now().isoformat()
        }
        
        summary_file = self.output_dir / 'scraping_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("=" * 60)
        logger.info("Scraping Agent Complete")
        logger.info("=" * 60)
        logger.info(f"Scraped: {self.scraped_count}")
        logger.info(f"Failed: {self.failed_count}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Summary saved to: {summary_file}")
        
        return summary


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Scraping Agent - Download articles from discovered locations")
    parser.add_argument('locations_csv', help='CSV file with discovered locations')
    parser.add_argument('--output-dir', default='scraped_knowledge', help='Output directory')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    parser.add_argument('--max-articles', type=int, help='Maximum articles to scrape')
    
    args = parser.parse_args()
    
    agent = ScrapingAgent(args.locations_csv, args.output_dir)
    agent.run(delay=args.delay, max_articles=args.max_articles)


if __name__ == "__main__":
    main()

