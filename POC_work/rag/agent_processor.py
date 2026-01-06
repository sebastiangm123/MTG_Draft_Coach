"""
Processing Agent
Processes scraped articles into vector database.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Import our existing modules
from content_processor import ContentProcessor
from vector_db_pipeline import VectorDBPipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProcessingAgent:
    """Agent that processes scraped content into vector database."""
    
    def __init__(
        self,
        scraped_dir: str = "scraped_knowledge",
        vector_db_path: str = "./vector_db",
        embedding_model: str = "openai",
        api_key: str = None
    ):
        """
        Initialize processing agent.
        
        Args:
            scraped_dir: Directory with scraped articles
            vector_db_path: Path to vector database
            embedding_model: "openai" or "local"
            api_key: OpenAI API key (if using OpenAI)
        """
        self.scraped_dir = Path(scraped_dir)
        self.vector_db_path = vector_db_path
        self.embedding_model = embedding_model
        self.api_key = api_key
        
        # Initialize components
        self.processor = ContentProcessor(chunk_size=1000, chunk_overlap=200)
        self.pipeline = None  # Will be initialized when needed
    
    def load_scraped_articles(self) -> List[Dict]:
        """Load all scraped articles from directory."""
        if not self.scraped_dir.exists():
            logger.error(f"Scraped directory not found: {self.scraped_dir}")
            return []
        
        articles = []
        json_files = list(self.scraped_dir.glob("*.json"))
        
        # Exclude summary file
        json_files = [f for f in json_files if f.name != 'scraping_summary.json']
        
        logger.info(f"Loading articles from {len(json_files)} files...")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    article = json.load(f)
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Error loading {json_file}: {e}")
                continue
        
        logger.info(f"Loaded {len(articles)} articles")
        return articles
    
    def process_articles(self, articles: List[Dict]) -> List[Dict]:
        """Process articles into chunks."""
        logger.info("Processing articles into chunks...")
        all_chunks = []
        
        for i, article in enumerate(articles, 1):
            if i % 10 == 0:
                logger.info(f"Processing article {i}/{len(articles)}...")
            
            chunks = self.processor.process_article(article)
            all_chunks.extend(chunks)
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(articles)} articles")
        return all_chunks
    
    def initialize_pipeline(self):
        """Initialize vector database pipeline."""
        if self.pipeline is None:
            logger.info("Initializing vector database pipeline...")
            self.pipeline = VectorDBPipeline(
                db_path=self.vector_db_path,
                embedding_model=self.embedding_model,
                api_key=self.api_key
            )
    
    def run(self, batch_size: int = 100):
        """
        Run processing agent.
        
        Args:
            batch_size: Batch size for embedding generation
        """
        logger.info("=" * 60)
        logger.info("Starting Processing Agent")
        logger.info("=" * 60)
        logger.info(f"Scraped directory: {self.scraped_dir}")
        logger.info(f"Vector database: {self.vector_db_path}")
        logger.info(f"Embedding model: {self.embedding_model}")
        
        # Step 1: Load articles
        articles = self.load_scraped_articles()
        if not articles:
            logger.error("No articles to process")
            return
        
        # Step 2: Process into chunks
        chunks = self.process_articles(articles)
        if not chunks:
            logger.error("No chunks created")
            return
        
        # Step 3: Initialize pipeline
        self.initialize_pipeline()
        
        # Step 4: Store in vector database
        logger.info("Storing chunks in vector database...")
        processed = self.pipeline.process_chunks(chunks, batch_size=batch_size)
        
        # Get stats
        stats = self.pipeline.get_stats()
        
        # Create summary
        summary = {
            'articles_processed': len(articles),
            'chunks_created': len(chunks),
            'chunks_stored': processed,
            'vector_db_path': self.vector_db_path,
            'embedding_model': self.embedding_model,
            'total_chunks_in_db': stats['total_chunks'],
            'sources': stats['sources'],
            'completed_at': datetime.now().isoformat()
        }
        
        summary_file = Path(self.vector_db_path).parent / 'processing_summary.json'
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info("=" * 60)
        logger.info("Processing Agent Complete")
        logger.info("=" * 60)
        logger.info(f"Articles processed: {len(articles)}")
        logger.info(f"Chunks created: {len(chunks)}")
        logger.info(f"Chunks stored: {processed}")
        logger.info(f"Total chunks in database: {stats['total_chunks']}")
        logger.info(f"Sources: {stats['sources']}")
        logger.info(f"Summary saved to: {summary_file}")
        
        return summary


def main():
    """Main function."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Processing Agent - Process scraped content into vector database")
    parser.add_argument('--scraped-dir', default='scraped_knowledge', help='Directory with scraped articles')
    parser.add_argument('--db-path', default='./vector_db', help='Vector database path')
    parser.add_argument('--model', choices=['openai', 'local'], default='openai', help='Embedding model')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for embeddings')
    
    args = parser.parse_args()
    
    # Get API key if using OpenAI
    api_key = None
    if args.model == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    
    agent = ProcessingAgent(
        scraped_dir=args.scraped_dir,
        vector_db_path=args.db_path,
        embedding_model=args.model,
        api_key=api_key
    )
    agent.run(batch_size=args.batch_size)


if __name__ == "__main__":
    main()

