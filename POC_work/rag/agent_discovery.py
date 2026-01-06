"""
Discovery Agent
Finds and documents locations of MTG draft articles and content online.
Outputs a CSV of locations to scrape.
"""

import csv
import time
import logging
from typing import List, Dict, Set
from pathlib import Path
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DiscoveryAgent:
    """Agent that discovers MTG draft content locations online."""
    
    def __init__(self, output_csv: str = "discovered_locations.csv", max_locations: int = 1000):
        """
        Initialize discovery agent.
        
        Args:
            output_csv: Path to output CSV file
            max_locations: Maximum locations to discover
        """
        self.output_csv = Path(output_csv)
        self.max_locations = max_locations
        self.discovered_locations: Set[str] = set()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Keywords to search for
        self.search_keywords = [
            "magic the gathering draft",
            "mtg limited",
            "draft strategy",
            "limited format",
            "draft guide",
            "mtg draft articles",
            "limited resources",
            "draft pick order",
            "mtg draft tier list",
            "limited format guide"
        ]
        
        # Known MTG content sites to explore
        self.known_sites = [
            "https://www.channelfireball.com",
            "https://www.starcitygames.com",
            "https://www.mtggoldfish.com",
            "https://www.tcgplayer.com",
            "https://www.draftsim.com",
            "https://www.17lands.com",
            "https://www.mtgtop8.com",
            "https://www.reddit.com/r/lrcast",
            "https://www.reddit.com/r/magicTCG",
            "https://www.reddit.com/r/spikes",
            "https://www.youtube.com",
            "https://www.twitch.tv",
            "https://www.patreon.com",
            "https://www.medium.com",
            "https://www.wordpress.com",
        ]
        
        # Patterns to identify draft content
        self.content_patterns = [
            r'/draft',
            r'/limited',
            r'/article',
            r'/guide',
            r'/strategy',
            r'/tier.*list',
            r'/pick.*order',
            r'/format.*guide',
            r'/set.*review',
            r'/card.*evaluation',
        ]
    
    def is_draft_content_url(self, url: str) -> bool:
        """Check if URL likely contains draft content."""
        url_lower = url.lower()
        
        # Check for draft-related keywords
        draft_keywords = ['draft', 'limited', 'lrcast', 'pick', 'archetype', 'format']
        if any(keyword in url_lower for keyword in draft_keywords):
            return True
        
        # Check for content patterns
        if any(re.search(pattern, url_lower) for pattern in self.content_patterns):
            return True
        
        return False
    
    def discover_from_site(self, base_url: str, max_pages: int = 10) -> List[Dict]:
        """Discover content locations from a specific site."""
        logger.info(f"Discovering from {base_url}")
        locations = []
        
        try:
            # Try to find sitemap
            sitemap_urls = [
                f"{base_url}/sitemap.xml",
                f"{base_url}/sitemap_index.xml",
                f"{base_url}/wp-sitemap.xml",
            ]
            
            for sitemap_url in sitemap_urls:
                try:
                    response = self.session.get(sitemap_url, timeout=10)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'xml')
                        urls = soup.find_all('url') or soup.find_all('loc')
                        
                        for url_elem in urls:
                            url = url_elem.text if hasattr(url_elem, 'text') else url_elem.string
                            if url and self.is_draft_content_url(url):
                                locations.append({
                                    'url': url,
                                    'source': base_url,
                                    'discovery_method': 'sitemap',
                                    'discovered_at': datetime.now().isoformat()
                                })
                                self.discovered_locations.add(url)
                        
                        if locations:
                            logger.info(f"Found {len(locations)} locations from {base_url} sitemap")
                            break
                except:
                    continue
            
            # If no sitemap, try crawling main pages
            if not locations:
                pages_to_check = [
                    f"{base_url}/articles",
                    f"{base_url}/draft",
                    f"{base_url}/limited",
                    f"{base_url}/guides",
                    f"{base_url}/strategy",
                ]
                
                for page_url in pages_to_check:
                    try:
                        response = self.session.get(page_url, timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Find all links
                            for link in soup.find_all('a', href=True):
                                href = link.get('href', '')
                                full_url = urljoin(base_url, href)
                                
                                if self.is_draft_content_url(full_url) and full_url not in self.discovered_locations:
                                    locations.append({
                                        'url': full_url,
                                        'source': base_url,
                                        'discovery_method': 'crawl',
                                        'discovered_at': datetime.now().isoformat()
                                    })
                                    self.discovered_locations.add(full_url)
                            
                            time.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.debug(f"Error checking {page_url}: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"Error discovering from {base_url}: {e}")
        
        return locations
    
    def discover_from_search_engines(self, max_results: int = 100) -> List[Dict]:
        """Discover locations using search engine queries."""
        logger.info("Discovering from search queries...")
        locations = []
        
        # Note: This is a simplified version. In production, you'd use:
        # - Google Custom Search API
        # - Bing Search API
        # - DuckDuckGo API
        # - Or scrape search results (with proper rate limiting)
        
        # For now, we'll use DuckDuckGo HTML scraping (simpler, no API key needed)
        try:
            from duckduckgo_search import DDGS
            
            for keyword in self.search_keywords:
                try:
                    with DDGS() as ddgs:
                        results = list(ddgs.text(
                            f"{keyword} site:channelfireball.com OR site:starcitygames.com OR site:mtggoldfish.com OR site:tcgplayer.com",
                            max_results=20
                        ))
                        
                        for result in results:
                            url = result.get('href', '')
                            if url and self.is_draft_content_url(url) and url not in self.discovered_locations:
                                locations.append({
                                    'url': url,
                                    'source': 'search_engine',
                                    'discovery_method': f'search_{keyword}',
                                    'discovered_at': datetime.now().isoformat()
                                })
                                self.discovered_locations.add(url)
                    
                    time.sleep(2)  # Rate limiting
                except Exception as e:
                    logger.debug(f"Error searching for {keyword}: {e}")
                    continue
        except ImportError:
            logger.warning("duckduckgo_search not installed. Install with: pip install duckduckgo-search")
            logger.info("Skipping search engine discovery")
        
        return locations
    
    def discover_from_reddit(self) -> List[Dict]:
        """Discover content from Reddit."""
        logger.info("Discovering from Reddit...")
        locations = []
        
        subreddits = ['lrcast', 'magicTCG', 'spikes', 'LimitedResources']
        
        for subreddit in subreddits:
            try:
                # Reddit JSON API (no auth needed for public data)
                url = f"https://www.reddit.com/r/{subreddit}/top.json?limit=100&t=all"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post in posts:
                        post_data = post.get('data', {})
                        post_url = post_data.get('url', '')
                        title = post_data.get('title', '')
                        
                        # Check if it's draft-related
                        if any(keyword in title.lower() for keyword in ['draft', 'limited', 'pick', 'archetype']):
                            if post_url not in self.discovered_locations:
                                locations.append({
                                    'url': post_url,
                                    'source': f'reddit/r/{subreddit}',
                                    'discovery_method': 'reddit_api',
                                    'title': title,
                                    'discovered_at': datetime.now().isoformat()
                                })
                                self.discovered_locations.add(post_url)
                
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.debug(f"Error discovering from Reddit r/{subreddit}: {e}")
        
        return locations
    
    def discover_from_youtube(self) -> List[Dict]:
        """Discover YouTube videos about MTG draft."""
        logger.info("Discovering from YouTube...")
        locations = []
        
        # YouTube search (simplified - in production use YouTube Data API)
        search_queries = [
            "mtg draft guide",
            "limited format strategy",
            "draft pick order",
            "mtg limited resources"
        ]
        
        for query in search_queries:
            try:
                # Using YouTube search URL (limited without API)
                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                response = self.session.get(search_url, timeout=10)
                
                if response.status_code == 200:
                    # Extract video IDs from page (simplified)
                    video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', response.text)
                    
                    for video_id in set(video_ids[:20]):  # Limit to 20 per query
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        if video_url not in self.discovered_locations:
                            locations.append({
                                'url': video_url,
                                'source': 'youtube',
                                'discovery_method': f'youtube_search_{query}',
                                'discovered_at': datetime.now().isoformat()
                            })
                            self.discovered_locations.add(video_url)
                
                time.sleep(2)  # Rate limiting
            except Exception as e:
                logger.debug(f"Error searching YouTube for {query}: {e}")
        
        return locations
    
    def save_locations(self, locations: List[Dict]):
        """Save discovered locations to CSV."""
        if not locations:
            logger.warning("No locations to save")
            return
        
        # Check if file exists to append or create
        file_exists = self.output_csv.exists()
        
        with open(self.output_csv, 'a', newline='', encoding='utf-8') as f:
            fieldnames = ['url', 'source', 'discovery_method', 'title', 'discovered_at', 'status']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            for loc in locations:
                # Ensure all fields exist
                row = {
                    'url': loc.get('url', ''),
                    'source': loc.get('source', ''),
                    'discovery_method': loc.get('discovery_method', ''),
                    'title': loc.get('title', ''),
                    'discovered_at': loc.get('discovered_at', ''),
                    'status': 'pending'
                }
                writer.writerow(row)
        
        logger.info(f"Saved {len(locations)} locations to {self.output_csv}")
    
    def run(self, duration_minutes: int = 30, max_file_size_gb: float = 1.0):
        """
        Run discovery agent.
        
        Args:
            duration_minutes: Maximum time to run (minutes)
            max_file_size_gb: Maximum file size before stopping (GB)
        """
        logger.info("=" * 60)
        logger.info("Starting Discovery Agent")
        logger.info("=" * 60)
        logger.info(f"Target duration: {duration_minutes} minutes")
        logger.info(f"Max file size: {max_file_size_gb} GB")
        logger.info(f"Max locations: {self.max_locations}")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        all_locations = []
        
        # Discovery methods
        discovery_methods = [
            ('Known Sites', self.discover_from_known_sites),
            ('Reddit', self.discover_from_reddit),
            ('YouTube', self.discover_from_youtube),
            ('Search Engines', self.discover_from_search_engines),
        ]
        
        for method_name, method_func in discovery_methods:
            if time.time() >= end_time:
                logger.info("Time limit reached")
                break
            
            if len(all_locations) >= self.max_locations:
                logger.info("Location limit reached")
                break
            
            # Check file size
            if self.output_csv.exists():
                file_size_gb = self.output_csv.stat().st_size / (1024 ** 3)
                if file_size_gb >= max_file_size_gb:
                    logger.info(f"File size limit reached: {file_size_gb:.2f} GB")
                    break
            
            try:
                logger.info(f"\nRunning discovery method: {method_name}")
                locations = method_func()
                all_locations.extend(locations)
                
                # Save incrementally
                if locations:
                    self.save_locations(locations)
                    logger.info(f"Total locations discovered: {len(all_locations)}")
                
            except Exception as e:
                logger.error(f"Error in {method_name}: {e}")
                continue
        
        logger.info("=" * 60)
        logger.info("Discovery Agent Complete")
        logger.info("=" * 60)
        logger.info(f"Total locations discovered: {len(all_locations)}")
        logger.info(f"Output file: {self.output_csv}")
        logger.info(f"File size: {self.output_csv.stat().st_size / (1024 ** 2):.2f} MB")
        
        return all_locations
    
    def discover_from_known_sites(self) -> List[Dict]:
        """Discover from known MTG content sites."""
        logger.info("Discovering from known sites...")
        all_locations = []
        
        for site in self.known_sites:
            if len(self.discovered_locations) >= self.max_locations:
                break
            
            locations = self.discover_from_site(site, max_pages=5)
            all_locations.extend(locations)
            time.sleep(2)  # Rate limiting between sites
        
        return all_locations


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discovery Agent - Find MTG draft content locations")
    parser.add_argument('--output', default='discovered_locations.csv', help='Output CSV file')
    parser.add_argument('--duration', type=int, default=30, help='Run duration in minutes')
    parser.add_argument('--max-size', type=float, default=1.0, help='Max file size in GB')
    parser.add_argument('--max-locations', type=int, default=1000, help='Max locations to discover')
    
    args = parser.parse_args()
    
    agent = DiscoveryAgent(output_csv=args.output, max_locations=args.max_locations)
    agent.run(duration_minutes=args.duration, max_file_size_gb=args.max_size)


if __name__ == "__main__":
    main()

