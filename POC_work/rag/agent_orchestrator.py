"""
Master Agent Orchestrator
Runs discovery, scraping, and processing agents in sequence.
"""

import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import os

from agent_discovery import DiscoveryAgent
from agent_scraper import ScrapingAgent
from agent_processor import ProcessingAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Orchestrates all agents to build the knowledge base."""
    
    def __init__(
        self,
        output_base_dir: str = "knowledge_base_output",
        embedding_model: str = "openai",
        api_key: str = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            output_base_dir: Base directory for all outputs
            embedding_model: "openai" or "local"
            api_key: OpenAI API key (if using OpenAI)
        """
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_model = embedding_model
        self.api_key = api_key
        
        # Define paths
        self.locations_csv = self.output_base_dir / "discovered_locations.csv"
        self.scraped_dir = self.output_base_dir / "scraped_knowledge"
        self.vector_db_path = str(self.output_base_dir / "vector_db")
        
        self.results = {
            'started_at': datetime.now().isoformat(),
            'discovery': {},
            'scraping': {},
            'processing': {},
            'completed_at': None,
            'success': False
        }
    
    def run_discovery_agent(
        self,
        duration_minutes: int = 30,
        max_file_size_gb: float = 1.0,
        max_locations: int = 1000,
        skip: bool = False
    ):
        """Run discovery agent."""
        if skip:
            if not self.locations_csv.exists():
                logger.error("Discovery skipped but locations CSV not found")
                return False
            logger.info("Skipping discovery agent (using existing locations)")
            return True
        
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 1: DISCOVERY AGENT")
        logger.info("=" * 60)
        
        agent = DiscoveryAgent(
            output_csv=str(self.locations_csv),
            max_locations=max_locations
        )
        
        try:
            locations = agent.run(
                duration_minutes=duration_minutes,
                max_file_size_gb=max_file_size_gb
            )
            
            self.results['discovery'] = {
                'locations_found': len(locations),
                'output_file': str(self.locations_csv),
                'file_size_mb': self.locations_csv.stat().st_size / (1024 ** 2) if self.locations_csv.exists() else 0
            }
            
            logger.info(f"Discovery complete: {len(locations)} locations found")
            return True
        
        except Exception as e:
            logger.error(f"Discovery agent failed: {e}", exc_info=True)
            self.results['discovery'] = {'error': str(e)}
            return False
    
    def run_scraping_agent(
        self,
        delay: float = 1.0,
        max_articles: int = None,
        skip: bool = False
    ):
        """Run scraping agent."""
        if skip:
            if not self.scraped_dir.exists() or not any(self.scraped_dir.glob("*.json")):
                logger.error("Scraping skipped but scraped directory is empty")
                return False
            logger.info("Skipping scraping agent (using existing scraped content)")
            return True
        
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2: SCRAPING AGENT")
        logger.info("=" * 60)
        
        if not self.locations_csv.exists():
            logger.error(f"Locations CSV not found: {self.locations_csv}")
            return False
        
        agent = ScrapingAgent(
            locations_csv=str(self.locations_csv),
            output_dir=str(self.scraped_dir)
        )
        
        try:
            summary = agent.run(delay=delay, max_articles=max_articles)
            
            self.results['scraping'] = {
                'scraped': summary.get('scraped', 0),
                'failed': summary.get('failed', 0),
                'output_dir': str(self.scraped_dir),
                'total_files': len(list(self.scraped_dir.glob("*.json"))) if self.scraped_dir.exists() else 0
            }
            
            logger.info(f"Scraping complete: {summary.get('scraped', 0)} articles scraped")
            return True
        
        except Exception as e:
            logger.error(f"Scraping agent failed: {e}", exc_info=True)
            self.results['scraping'] = {'error': str(e)}
            return False
    
    def run_processing_agent(
        self,
        batch_size: int = 100,
        skip: bool = False
    ):
        """Run processing agent."""
        if skip:
            logger.info("Skipping processing agent (using existing vector database)")
            return True
        
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 3: PROCESSING AGENT")
        logger.info("=" * 60)
        
        if not self.scraped_dir.exists():
            logger.error(f"Scraped directory not found: {self.scraped_dir}")
            return False
        
        agent = ProcessingAgent(
            scraped_dir=str(self.scraped_dir),
            vector_db_path=self.vector_db_path,
            embedding_model=self.embedding_model,
            api_key=self.api_key
        )
        
        try:
            summary = agent.run(batch_size=batch_size)
            
            self.results['processing'] = {
                'articles_processed': summary.get('articles_processed', 0),
                'chunks_created': summary.get('chunks_created', 0),
                'chunks_stored': summary.get('chunks_stored', 0),
                'total_chunks_in_db': summary.get('total_chunks_in_db', 0),
                'vector_db_path': self.vector_db_path
            }
            
            logger.info(f"Processing complete: {summary.get('chunks_stored', 0)} chunks stored")
            return True
        
        except Exception as e:
            logger.error(f"Processing agent failed: {e}", exc_info=True)
            self.results['processing'] = {'error': str(e)}
            return False
    
    def run_full_pipeline(
        self,
        discovery_duration: int = 30,
        discovery_max_size: float = 1.0,
        discovery_max_locations: int = 1000,
        scraping_delay: float = 1.0,
        scraping_max_articles: int = None,
        processing_batch_size: int = 100,
        skip_discovery: bool = False,
        skip_scraping: bool = False,
        skip_processing: bool = False
    ):
        """
        Run the full pipeline: discovery -> scraping -> processing.
        
        Args:
            discovery_duration: Discovery agent run time (minutes)
            discovery_max_size: Max CSV file size (GB)
            discovery_max_locations: Max locations to discover
            scraping_delay: Delay between scraping requests (seconds)
            scraping_max_articles: Max articles to scrape (None = all)
            processing_batch_size: Batch size for embeddings
            skip_discovery: Skip discovery phase
            skip_scraping: Skip scraping phase
            skip_processing: Skip processing phase
        """
        logger.info("=" * 60)
        logger.info("KNOWLEDGE BASE BUILDING PIPELINE")
        logger.info("=" * 60)
        logger.info(f"Output directory: {self.output_base_dir}")
        logger.info(f"Embedding model: {self.embedding_model}")
        logger.info("")
        
        # Phase 1: Discovery
        discovery_success = self.run_discovery_agent(
            duration_minutes=discovery_duration,
            max_file_size_gb=discovery_max_size,
            max_locations=discovery_max_locations,
            skip=skip_discovery
        )
        
        if not discovery_success and not skip_discovery:
            logger.error("Discovery phase failed. Stopping pipeline.")
            self.results['completed_at'] = datetime.now().isoformat()
            self.save_results()
            return False
        
        # Phase 2: Scraping
        scraping_success = self.run_scraping_agent(
            delay=scraping_delay,
            max_articles=scraping_max_articles,
            skip=skip_scraping
        )
        
        if not scraping_success and not skip_scraping:
            logger.error("Scraping phase failed. Stopping pipeline.")
            self.results['completed_at'] = datetime.now().isoformat()
            self.save_results()
            return False
        
        # Phase 3: Processing
        processing_success = self.run_processing_agent(
            batch_size=processing_batch_size,
            skip=skip_processing
        )
        
        if not processing_success and not skip_processing:
            logger.error("Processing phase failed.")
            self.results['completed_at'] = datetime.now().isoformat()
            self.save_results()
            return False
        
        # Success
        self.results['success'] = True
        self.results['completed_at'] = datetime.now().isoformat()
        
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE COMPLETE!")
        logger.info("=" * 60)
        self.print_summary()
        self.save_results()
        
        return True
    
    def print_summary(self):
        """Print pipeline summary."""
        logger.info("\nSummary:")
        logger.info(f"  Discovery: {self.results['discovery'].get('locations_found', 0)} locations")
        logger.info(f"  Scraping: {self.results['scraping'].get('scraped', 0)} articles")
        logger.info(f"  Processing: {self.results['processing'].get('chunks_stored', 0)} chunks in vector DB")
        logger.info(f"\nVector database ready at: {self.vector_db_path}")
    
    def save_results(self):
        """Save pipeline results to JSON."""
        results_file = self.output_base_dir / "pipeline_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nResults saved to: {results_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent Orchestrator - Build MTG knowledge base with multi-agent system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (30 min discovery, then scrape and process)
  python agent_orchestrator.py
  
  # Use local embeddings (no API key)
  python agent_orchestrator.py --model local
  
  # Skip discovery (use existing locations)
  python agent_orchestrator.py --skip-discovery
  
  # Skip discovery and scraping (use existing scraped content)
  python agent_orchestrator.py --skip-discovery --skip-scraping
  
  # Custom discovery duration and file size
  python agent_orchestrator.py --discovery-duration 60 --discovery-max-size 2.0
        """
    )
    
    # General options
    parser.add_argument('--output-dir', default='knowledge_base_output', help='Output base directory')
    parser.add_argument('--model', choices=['openai', 'local'], default='openai', help='Embedding model')
    
    # Discovery options
    parser.add_argument('--discovery-duration', type=int, default=30, help='Discovery duration (minutes)')
    parser.add_argument('--discovery-max-size', type=float, default=1.0, help='Max CSV file size (GB)')
    parser.add_argument('--discovery-max-locations', type=int, default=1000, help='Max locations to discover')
    parser.add_argument('--skip-discovery', action='store_true', help='Skip discovery phase')
    
    # Scraping options
    parser.add_argument('--scraping-delay', type=float, default=1.0, help='Delay between requests (seconds)')
    parser.add_argument('--scraping-max-articles', type=int, help='Max articles to scrape')
    parser.add_argument('--skip-scraping', action='store_true', help='Skip scraping phase')
    
    # Processing options
    parser.add_argument('--processing-batch-size', type=int, default=100, help='Batch size for embeddings')
    parser.add_argument('--skip-processing', action='store_true', help='Skip processing phase')
    
    args = parser.parse_args()
    
    # Get API key if using OpenAI
    api_key = None
    if args.model == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Will try to use OpenAI client default.")
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(
        output_base_dir=args.output_dir,
        embedding_model=args.model,
        api_key=api_key
    )
    
    # Run pipeline
    try:
        success = orchestrator.run_full_pipeline(
            discovery_duration=args.discovery_duration,
            discovery_max_size=args.discovery_max_size,
            discovery_max_locations=args.discovery_max_locations,
            scraping_delay=args.scraping_delay,
            scraping_max_articles=args.scraping_max_articles,
            processing_batch_size=args.processing_batch_size,
            skip_discovery=args.skip_discovery,
            skip_scraping=args.skip_scraping,
            skip_processing=args.skip_processing
        )
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.info("\n\nPipeline interrupted by user")
        orchestrator.save_results()
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nPipeline failed: {e}", exc_info=True)
        orchestrator.save_results()
        sys.exit(1)


if __name__ == "__main__":
    main()

