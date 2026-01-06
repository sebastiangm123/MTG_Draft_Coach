"""
Master script to build the MTG knowledge base from web scraping.
Orchestrates scraping, processing, and vector database creation.
"""

import argparse
import sys
from pathlib import Path
import logging
from typing import Optional

# Import our modules
from mtg_content_scraper import MTGContentScraper
from content_processor import ContentProcessor
from vector_db_pipeline import VectorDBPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KnowledgeBaseBuilder:
    """Orchestrates the entire knowledge base building process."""
    
    def __init__(
        self,
        scraped_dir: str = "scraped_content",
        processed_dir: str = "processed_content",
        vector_db_path: str = "./vector_db",
        embedding_model: str = "openai",
        api_key: Optional[str] = None
    ):
        """Initialize the builder."""
        self.scraped_dir = Path(scraped_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(exist_ok=True)
        self.vector_db_path = vector_db_path
        self.embedding_model = embedding_model
        self.api_key = api_key
    
    def scrape_content(self, sources: Optional[list] = None, max_articles: int = 30) -> Path:
        """Step 1: Scrape content from web sources."""
        logger.info("=" * 60)
        logger.info("STEP 1: Scraping MTG content from web sources")
        logger.info("=" * 60)
        
        scraper = MTGContentScraper(
            output_dir=str(self.scraped_dir),
            delay=1.5  # Be respectful with rate limiting
        )
        
        if sources:
            # Scrape specific sources
            all_articles = []
            for source in sources:
                if source in scraper.sources:
                    articles = scraper.scrape_source(source, max_articles)
                    all_articles.extend(articles)
                else:
                    logger.warning(f"Unknown source: {source}")
        else:
            # Scrape all sources
            all_articles = scraper.scrape_all_sources(max_articles_per_source=max_articles)
        
        output_file = self.scraped_dir / "all_articles.json"
        logger.info(f"Scraping complete. Articles saved to: {output_file}")
        return output_file
    
    def process_content(self, articles_file: Path) -> Path:
        """Step 2: Process articles into chunks."""
        logger.info("=" * 60)
        logger.info("STEP 2: Processing articles into chunks")
        logger.info("=" * 60)
        
        processor = ContentProcessor(chunk_size=1000, chunk_overlap=200)
        chunks = processor.process_articles_file(str(articles_file))
        
        output_file = self.processed_dir / "processed_chunks.json"
        processor.save_chunks(chunks, str(output_file))
        
        logger.info(f"Processing complete. Chunks saved to: {output_file}")
        return output_file
    
    def build_vector_db(self, chunks_file: Path) -> VectorDBPipeline:
        """Step 3: Build vector database from chunks."""
        logger.info("=" * 60)
        logger.info("STEP 3: Building vector database")
        logger.info("=" * 60)
        
        pipeline = VectorDBPipeline(
            db_path=self.vector_db_path,
            embedding_model=self.embedding_model,
            api_key=self.api_key
        )
        
        processed = pipeline.process_chunks_file(str(chunks_file), batch_size=100)
        
        stats = pipeline.get_stats()
        logger.info(f"Vector database complete!")
        logger.info(f"  Total chunks: {stats['total_chunks']}")
        logger.info(f"  Sources: {stats['sources']}")
        
        return pipeline
    
    def build_full_pipeline(
        self,
        skip_scrape: bool = False,
        skip_process: bool = False,
        sources: Optional[list] = None,
        max_articles: int = 30
    ) -> VectorDBPipeline:
        """
        Run the full pipeline: scrape -> process -> vectorize.
        
        Args:
            skip_scrape: Skip scraping step (use existing articles)
            skip_process: Skip processing step (use existing chunks)
            sources: List of sources to scrape (None = all)
            max_articles: Max articles per source
        """
        articles_file = self.scraped_dir / "all_articles.json"
        chunks_file = self.processed_dir / "processed_chunks.json"
        
        # Step 1: Scrape
        if not skip_scrape:
            articles_file = self.scrape_content(sources, max_articles)
        elif not articles_file.exists():
            logger.error(f"Articles file not found: {articles_file}")
            logger.error("Run without --skip-scrape to scrape content first")
            sys.exit(1)
        
        # Step 2: Process
        if not skip_process:
            chunks_file = self.process_content(articles_file)
        elif not chunks_file.exists():
            logger.error(f"Chunks file not found: {chunks_file}")
            logger.error("Run without --skip-process to process articles first")
            sys.exit(1)
        
        # Step 3: Build vector DB
        pipeline = self.build_vector_db(chunks_file)
        
        logger.info("=" * 60)
        logger.info("KNOWLEDGE BASE BUILD COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"Vector database location: {self.vector_db_path}")
        logger.info(f"You can now use the vector database for RAG queries")
        
        return pipeline


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build MTG knowledge base from web scraping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (scrape, process, vectorize)
  python build_knowledge_base.py
  
  # Skip scraping (use existing articles)
  python build_knowledge_base.py --skip-scrape
  
  # Skip scraping and processing (use existing chunks)
  python build_knowledge_base.py --skip-scrape --skip-process
  
  # Scrape only specific sources
  python build_knowledge_base.py --sources channelfireball mtggoldfish
  
  # Use local embeddings (no API key needed)
  python build_knowledge_base.py --model local
        """
    )
    
    parser.add_argument(
        '--skip-scrape',
        action='store_true',
        help='Skip scraping step (use existing articles.json)'
    )
    parser.add_argument(
        '--skip-process',
        action='store_true',
        help='Skip processing step (use existing chunks.json)'
    )
    parser.add_argument(
        '--sources',
        nargs='+',
        help='Specific sources to scrape (default: all)',
        choices=['channelfireball', 'starcitygames', 'mtggoldfish', 'tcgplayer', 'reddit']
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        default=30,
        help='Max articles per source (default: 30)'
    )
    parser.add_argument(
        '--model',
        choices=['openai', 'local'],
        default='openai',
        help='Embedding model to use (default: openai)'
    )
    parser.add_argument(
        '--db-path',
        default='./vector_db',
        help='Path to vector database (default: ./vector_db)'
    )
    parser.add_argument(
        '--scraped-dir',
        default='scraped_content',
        help='Directory for scraped content (default: scraped_content)'
    )
    parser.add_argument(
        '--processed-dir',
        default='processed_content',
        help='Directory for processed content (default: processed_content)'
    )
    
    args = parser.parse_args()
    
    # Check for API key if using OpenAI
    api_key = None
    if args.model == "openai":
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Will try to use OpenAI client default.")
    
    # Build knowledge base
    builder = KnowledgeBaseBuilder(
        scraped_dir=args.scraped_dir,
        processed_dir=args.processed_dir,
        vector_db_path=args.db_path,
        embedding_model=args.model,
        api_key=api_key
    )
    
    try:
        pipeline = builder.build_full_pipeline(
            skip_scrape=args.skip_scrape,
            skip_process=args.skip_process,
            sources=args.sources,
            max_articles=args.max_articles
        )
        
        # Test the pipeline
        logger.info("\n" + "=" * 60)
        logger.info("Testing vector database search...")
        logger.info("=" * 60)
        test_queries = [
            "What are the best draft strategies?",
            "How do I evaluate cards in limited?",
            "What makes a good mana curve?"
        ]
        
        for query in test_queries:
            logger.info(f"\nQuery: {query}")
            results = pipeline.search(query, n_results=2)
            if results:
                logger.info(f"  Found {len(results)} results")
                for i, result in enumerate(results, 1):
                    title = result['metadata'].get('title', 'No title')
                    source = result['metadata'].get('source', 'unknown')
                    logger.info(f"  {i}. {title} ({source})")
            else:
                logger.info("  No results found")
        
    except KeyboardInterrupt:
        logger.info("\n\nBuild interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nError building knowledge base: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

