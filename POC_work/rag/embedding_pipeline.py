#!/usr/bin/env python3
"""
Embedding Pipeline for MTG Draft Coach RAG System

Generates embeddings for all chunks and stores them in vector database.
Integrates Parts 1-5: Query Processor → Knowledge Base Extractor → Text Chunker → Embedding Generator → Vector Database
"""

import os
import sys
import sqlite3
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.text_chunker import TextChunker, TextChunk
from rag.knowledge_base_extractor import KnowledgeBaseExtractor, ExtractedContext
from rag.embedding_generator import EmbeddingGenerator
from rag.vector_database import VectorDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """
    Pipeline to generate embeddings for all database content and store in vector database.
    """
    
    def __init__(
        self,
        db_path: str = "mtg_draft_coach.db",
        vector_db_path: str = "./vector_db",
        embedding_model: str = "openai",
        api_key: Optional[str] = None,
        reset_vector_db: bool = False
    ):
        """
        Initialize embedding pipeline.
        
        Args:
            db_path: Path to SQLite database
            vector_db_path: Path to vector database storage
            embedding_model: "openai" or "local"
            api_key: OpenAI API key (if using OpenAI)
            reset_vector_db: If True, reset vector database before processing
        """
        self.db_path = Path(db_path)
        self.extractor = KnowledgeBaseExtractor(str(self.db_path))
        self.chunker = TextChunker()
        self.embedding_generator = EmbeddingGenerator(
            model=embedding_model,
            api_key=api_key
        )
        self.vector_db = VectorDatabase(
            db_path=vector_db_path,
            reset=reset_vector_db
        )
        
        logger.info("Initialized embedding pipeline")
        logger.info(f"  Database: {db_path}")
        logger.info(f"  Vector DB: {vector_db_path}")
        logger.info(f"  Embedding Model: {embedding_model}")
    
    def process_all_cards(
        self,
        set_code: Optional[str] = None,
        batch_size: int = 100,
        max_cards: Optional[int] = None
    ) -> int:
        """
        Process all cards from database into vector database.
        
        Args:
            set_code: Filter by set code (optional)
            batch_size: Batch size for processing
            max_cards: Maximum number of cards to process (optional)
            
        Returns:
            Number of chunks processed
        """
        logger.info("Processing all cards from database...")
        
        chunks_processed = 0
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Query all cards
                query = """
                    SELECT DISTINCT
                        c.card_id,
                        c.card_name,
                        c."set",
                        c.color_identity,
                        c.card_type,
                        c.cmc,
                        c.rarity,
                        cs.gih_wr,
                        cs.drawn_wr,
                        cs.overall_wr,
                        cs.avg_pick_number,
                        cs.maindeck_rate,
                        cs.gih_games,
                        cs.drawn_games,
                        cs.total_games
                    FROM cards c
                    LEFT JOIN card_statistics cs ON c.card_id = cs.card_id AND c."set" = cs."set"
                    WHERE 1=1
                """
                params = []
                
                if set_code:
                    query += ' AND c."set" = ?'
                    params.append(set_code.upper())
                
                query += " ORDER BY c.card_id"
                
                if max_cards:
                    query += " LIMIT ?"
                    params.append(max_cards)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                logger.info(f"Found {len(rows)} cards to process")
                
                # Process in batches
                for i in range(0, len(rows), batch_size):
                    batch_rows = rows[i:i + batch_size]
                    batch_chunks = []
                    
                    # Convert rows to CardData and chunk
                    from rag.knowledge_base_extractor import CardData
                    
                    def _safe_get(row, key, default=None):
                        """Safely get value from sqlite3.Row."""
                        try:
                            return row[key] if key in row.keys() else default
                        except (KeyError, TypeError):
                            return default
                    
                    for row in batch_rows:
                        card = CardData(
                            card_id=row['card_id'],
                            card_name=row['card_name'],
                            set=row['set'],
                            color_identity=_safe_get(row, 'color_identity'),
                            card_type=_safe_get(row, 'card_type'),
                            cmc=_safe_get(row, 'cmc'),
                            rarity=_safe_get(row, 'rarity'),
                            gih_wr=_safe_get(row, 'gih_wr'),
                            drawn_wr=_safe_get(row, 'drawn_wr'),
                            overall_wr=_safe_get(row, 'overall_wr'),
                            avg_pick_number=_safe_get(row, 'avg_pick_number'),
                            maindeck_rate=_safe_get(row, 'maindeck_rate'),
                            gih_games=_safe_get(row, 'gih_games'),
                            drawn_games=_safe_get(row, 'drawn_games'),
                            total_games=_safe_get(row, 'total_games')
                        )
                        
                        chunk = self.chunker._chunk_card(card)
                        if chunk:
                            batch_chunks.append(chunk)
                    
                    # Generate embeddings and store
                    if batch_chunks:
                        self._process_chunks(batch_chunks)
                        chunks_processed += len(batch_chunks)
                        logger.info(f"Processed {chunks_processed}/{len(rows)} cards")
        
        except Exception as e:
            logger.error(f"Error processing cards: {e}")
            raise
        
        logger.info(f"Completed processing {chunks_processed} card chunks")
        return chunks_processed
    
    def process_all_archetypes(
        self,
        set_code: Optional[str] = None,
        batch_size: int = 50
    ) -> int:
        """
        Process all archetypes from database into vector database.
        
        Args:
            set_code: Filter by set code (optional)
            batch_size: Batch size for processing
            
        Returns:
            Number of chunks processed
        """
        logger.info("Processing all archetypes from database...")
        
        chunks_processed = 0
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT 
                        ca.archetype_id,
                        ca.main_colors,
                        ca.splash_colors,
                        ca.full_color_identity,
                        ca."set",
                        ca.event_type,
                        ca.win_rate,
                        ca.total_games,
                        ca.total_wins,
                        ca.avg_num_turns
                    FROM color_archetypes ca
                    WHERE 1=1
                """
                params = []
                
                if set_code:
                    query += ' AND ca."set" = ?'
                    params.append(set_code.upper())
                
                query += " ORDER BY ca.archetype_id"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                logger.info(f"Found {len(rows)} archetypes to process")
                
                # Process in batches
                for i in range(0, len(rows), batch_size):
                    batch_rows = rows[i:i + batch_size]
                    batch_chunks = []
                    
                    from rag.knowledge_base_extractor import ArchetypeData
                    
                    def _safe_get(row, key, default=None):
                        """Safely get value from sqlite3.Row."""
                        try:
                            return row[key] if key in row.keys() else default
                        except (KeyError, TypeError):
                            return default
                    
                    for row in batch_rows:
                        archetype = ArchetypeData(
                            archetype_id=row['archetype_id'],
                            main_colors=row['main_colors'],
                            splash_colors=_safe_get(row, 'splash_colors'),
                            full_color_identity=_safe_get(row, 'full_color_identity'),
                            set=row['set'],
                            event_type=_safe_get(row, 'event_type'),
                            win_rate=_safe_get(row, 'win_rate'),
                            total_games=_safe_get(row, 'total_games'),
                            total_wins=_safe_get(row, 'total_wins'),
                            avg_num_turns=_safe_get(row, 'avg_num_turns')
                        )
                        
                        chunk = self.chunker._chunk_archetype(archetype)
                        if chunk:
                            batch_chunks.append(chunk)
                    
                    if batch_chunks:
                        self._process_chunks(batch_chunks)
                        chunks_processed += len(batch_chunks)
                        logger.info(f"Processed {chunks_processed}/{len(rows)} archetypes")
        
        except Exception as e:
            logger.error(f"Error processing archetypes: {e}")
            raise
        
        logger.info(f"Completed processing {chunks_processed} archetype chunks")
        return chunks_processed
    
    def _process_chunks(self, chunks: List[TextChunk]):
        """
        Process a batch of chunks: generate embeddings and store in vector database.
        
        Args:
            chunks: List of TextChunk objects
        """
        if not chunks:
            return
        
        # Extract texts
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embedding_generator.generate_batch_embeddings(
            texts,
            batch_size=len(texts),
            show_progress=False
        )
        
        # Prepare metadata
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        metadatas = []
        for chunk in chunks:
            metadata = chunk.metadata.copy()
            metadata['text'] = chunk.text  # Store text in metadata for retrieval
            metadatas.append(metadata)
        
        # Store in vector database
        self.vector_db.add_chunks(
            chunk_ids=chunk_ids,
            embeddings=embeddings,
            texts=texts,
            metadatas=metadatas,
            batch_size=len(chunks)
        )
    
    def run_full_pipeline(
        self,
        set_code: Optional[str] = None,
        max_cards: Optional[int] = None,
        process_archetypes: bool = True
    ) -> Dict[str, int]:
        """
        Run full pipeline: process all cards and archetypes.
        
        Args:
            set_code: Filter by set code (optional)
            max_cards: Maximum number of cards to process (optional)
            process_archetypes: Whether to process archetypes
            
        Returns:
            Dictionary with counts of processed chunks
        """
        logger.info("=" * 80)
        logger.info("STARTING FULL EMBEDDING PIPELINE")
        logger.info("=" * 80)
        
        results = {
            "cards": 0,
            "archetypes": 0,
            "total": 0
        }
        
        # Process cards
        results["cards"] = self.process_all_cards(
            set_code=set_code,
            max_cards=max_cards
        )
        
        # Process archetypes
        if process_archetypes:
            results["archetypes"] = self.process_all_archetypes(
                set_code=set_code
            )
        
        results["total"] = results["cards"] + results["archetypes"]
        
        # Get final stats
        db_info = self.vector_db.get_collection_info()
        
        logger.info("=" * 80)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Cards processed: {results['cards']}")
        logger.info(f"Archetypes processed: {results['archetypes']}")
        logger.info(f"Total chunks: {results['total']}")
        logger.info(f"Vector DB total: {db_info.get('total_chunks', 0)}")
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MTG Draft Coach Embedding Pipeline")
    parser.add_argument('--db', default='mtg_draft_coach.db', help='Database path')
    parser.add_argument('--vector-db', default='./vector_db', help='Vector database path')
    parser.add_argument('--model', choices=['openai', 'local'], default='openai', help='Embedding model')
    parser.add_argument('--set', help='Filter by set code (e.g., TLA)')
    parser.add_argument('--max-cards', type=int, help='Maximum number of cards to process')
    parser.add_argument('--reset', action='store_true', help='Reset vector database before processing')
    parser.add_argument('--no-archetypes', action='store_true', help='Skip archetype processing')
    
    args = parser.parse_args()
    
    # Get API key if using OpenAI
    api_key = None
    if args.model == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
    
    # Initialize and run pipeline
    pipeline = EmbeddingPipeline(
        db_path=args.db,
        vector_db_path=args.vector_db,
        embedding_model=args.model,
        api_key=api_key,
        reset_vector_db=args.reset
    )
    
    results = pipeline.run_full_pipeline(
        set_code=args.set,
        max_cards=args.max_cards,
        process_archetypes=not args.no_archetypes
    )
    
    print(f"\nPipeline complete!")
    print(f"  Cards: {results['cards']}")
    print(f"  Archetypes: {results['archetypes']}")
    print(f"  Total: {results['total']}")


if __name__ == "__main__":
    main()

