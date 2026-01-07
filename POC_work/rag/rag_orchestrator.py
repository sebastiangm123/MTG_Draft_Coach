#!/usr/bin/env python3
"""
RAG Orchestrator for MTG Draft Coach

Part 10 of RAG Components Plan:
- Coordinates all RAG components
- Complete pipeline from query to answer
- Production-ready MTG Draft Coach agent
"""

import os
from typing import Dict, Optional, Any, List
from pathlib import Path
import logging

from rag.mtg_draft_query_processor import MTGDraftQueryProcessor
from rag.knowledge_base_extractor import KnowledgeBaseExtractor
from rag.text_chunker import TextChunker
from rag.embedding_generator import EmbeddingGenerator
from rag.vector_database import VectorDatabase
from rag.retrieval_system import RetrievalSystem
from rag.context_assembler import ContextAssembler
from rag.llm_integration import MTGDraftCoachLLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MTGDraftCoachRAG:
    """
    Complete RAG system for MTG Draft Coach.
    Coordinates all components to answer draft-related questions.
    """
    
    def __init__(
        self,
        db_path: str = "mtg_draft_coach.db",
        vector_db_path: str = "./vector_db",
        embedding_model: str = "openai",
        llm_model: str = "gpt-4",
        api_key: Optional[str] = None,
        enable_context: bool = True
    ):
        """
        Initialize MTG Draft Coach RAG system.
        
        Args:
            db_path: Path to SQLite database
            vector_db_path: Path to vector database
            embedding_model: "openai" or "local" for embeddings
            llm_model: OpenAI model for LLM (e.g., "gpt-4", "gpt-3.5-turbo")
            api_key: OpenAI API key (if None, reads from env)
            enable_context: Enable conversation context
        """
        logger.info("Initializing MTG Draft Coach RAG system...")
        
        # Get API key
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Initialize components
        self.query_processor = MTGDraftQueryProcessor(
            db_path=db_path,
            enable_context=enable_context
        )
        
        self.knowledge_extractor = KnowledgeBaseExtractor(db_path=db_path)
        
        self.text_chunker = TextChunker()
        
        self.embedding_generator = EmbeddingGenerator(
            model=embedding_model,
            api_key=self.api_key
        )
        
        self.vector_db = VectorDatabase(
            db_path=vector_db_path,
            collection_name="mtg_draft_coach"
        )
        
        self.retrieval = RetrievalSystem(
            vector_db=self.vector_db,
            embedding_generator=self.embedding_generator
        )
        
        self.context_assembler = ContextAssembler()
        
        # Initialize LLM (optional - may fail if no API key)
        try:
            self.llm = MTGDraftCoachLLM(
                api_key=self.api_key,
                model=llm_model
            )
            self.llm_available = True
        except (ValueError, Exception) as e:
            if "OPENAI_API_KEY" in str(e) or "API key" in str(e):
                logger.warning(f"LLM not available: {e}. Parts 1-7 will work, Part 8 requires API key.")
                self.llm = None
                self.llm_available = False
            else:
                raise
        
        logger.info("MTG Draft Coach RAG system initialized")
        logger.info(f"  Database: {db_path}")
        logger.info(f"  Vector DB: {vector_db_path}")
        logger.info(f"  Embedding Model: {embedding_model}")
        logger.info(f"  LLM Model: {llm_model}")
    
    def answer(
        self,
        query: str,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Answer a user query using the complete RAG pipeline.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve
            include_sources: Whether to include source information
            
        Returns:
            Dictionary with 'answer', 'sources', 'query_info', etc.
        """
        logger.info(f"Processing query: {query}")
        
        try:
            # Step 1: Process query
            processed_query = self.query_processor.process(query)
            logger.debug(f"Query intent: {processed_query.intent.value}")
            logger.debug(f"Entities: {processed_query.entities}")
            
            # Step 2: Retrieve relevant context
            retrieved_chunks = self.retrieval.retrieve_with_query_processor(
                processed_query=processed_query,
                top_k=top_k
            )
            logger.info(f"Retrieved {len(retrieved_chunks)} chunks")
            
            # If no chunks retrieved, try without filters
            if not retrieved_chunks:
                logger.warning("No chunks retrieved with filters, trying without filters")
                retrieved_chunks = self.retrieval.retrieve(
                    query=processed_query.rewritten_query or processed_query.original_query,
                    top_k=top_k
                )
            
            # Step 3: Generate answer with context
            if self.llm_available and self.llm:
                if retrieved_chunks:
                    result = self.llm.answer_with_context(
                        user_query=query,
                        retrieved_chunks=retrieved_chunks
                    )
                else:
                    # Fallback: answer without context
                    logger.warning("No context available, answering without RAG")
                    result = {
                        'answer': self.llm.answer_simple(query),
                        'sources': [],
                        'chunks_used': 0,
                        'tokens_estimated': 0,
                        'context_length': 0
                    }
            else:
                # LLM not available - return context information
                logger.info("LLM not available, returning context information")
                assembled = self.context_assembler.assemble(retrieved_chunks, query)
                result = {
                    'answer': f"Retrieved {len(retrieved_chunks)} relevant chunks.\n\n"
                             f"To get AI-generated answers, set OPENAI_API_KEY environment variable.\n\n"
                             f"Retrieved Context:\n{assembled['context'][:1000]}...",
                    'sources': [
                        {
                            'id': chunk.get('id'),
                            'type': chunk.get('metadata', {}).get('chunk_type'),
                            'source': self.context_assembler._get_source_info(chunk),
                            'distance': chunk.get('distance')
                        }
                        for chunk in retrieved_chunks[:5]
                    ],
                    'chunks_used': assembled['chunks_used'],
                    'tokens_estimated': assembled['tokens_estimated'],
                    'context_length': len(assembled['context']),
                    'retrieval_info': {
                        'chunks_retrieved': len(retrieved_chunks),
                        'chunks_used': assembled['chunks_used'],
                        'context_length': len(assembled['context']),
                        'tokens_estimated': assembled['tokens_estimated']
                    }
                }
            
            # Build response
            response = {
                'answer': result['answer'],
                'query_info': {
                    'original_query': query,
                    'intent': processed_query.intent.value,
                    'query_type': processed_query.query_type.value,
                    'entities': {
                        'cards': processed_query.entities.cards,
                        'archetypes': processed_query.entities.archetypes,
                        'sets': processed_query.entities.set_codes
                    },
                    'confidence': processed_query.confidence
                },
                'retrieval_info': {
                    'chunks_retrieved': len(retrieved_chunks),
                    'chunks_used': result['chunks_used'],
                    'context_length': result.get('context_length', 0),
                    'tokens_estimated': result.get('tokens_estimated', 0)
                }
            }
            
            if include_sources and result.get('sources'):
                response['sources'] = result['sources']
            
            logger.info("Query processed successfully")
            return response
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return {
                'answer': f"I encountered an error processing your query: {str(e)}. Please try rephrasing your question.",
                'error': str(e),
                'query_info': {'original_query': query}
            }
    
    def answer_simple(self, query: str) -> str:
        """
        Get simple answer string (without full metadata).
        
        Args:
            query: User query
            
        Returns:
            Answer string
        """
        result = self.answer(query, include_sources=False)
        return result.get('answer', '')
    
    def clear_conversation(self):
        """Clear conversation context."""
        self.query_processor.context.clear() if self.query_processor.context else None
        if self.llm_available and self.llm:
            self.llm.clear_conversation()
        logger.info("Conversation context cleared")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the RAG system."""
        db_info = self.vector_db.get_collection_info()
        embedding_info = self.embedding_generator.get_model_info()
        
        return {
            'vector_db': db_info,
            'embedding_model': embedding_info,
            'llm_model': self.llm.model if self.llm_available and self.llm else 'Not Available',
            'llm_available': self.llm_available,
            'context_enabled': self.query_processor.enable_context
        }


def main():
    """Example usage of MTG Draft Coach RAG."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MTG Draft Coach RAG Agent")
    parser.add_argument('--db', default='mtg_draft_coach.db', help='Database path')
    parser.add_argument('--vector-db', default='./vector_db', help='Vector database path')
    parser.add_argument('--model', choices=['openai', 'local'], default='openai', help='Embedding model')
    parser.add_argument('--llm-model', default='gpt-4', help='LLM model')
    parser.add_argument('--query', help='Single query to process')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    # Initialize RAG system
    rag = MTGDraftCoachRAG(
        db_path=args.db,
        vector_db_path=args.vector_db,
        embedding_model=args.model,
        llm_model=args.llm_model
    )
    
    if args.query:
        # Single query
        result = rag.answer(args.query)
        print("\n" + "=" * 80)
        print("ANSWER")
        print("=" * 80)
        print(result['answer'])
        if result.get('sources'):
            print("\n" + "=" * 80)
            print("SOURCES")
            print("=" * 80)
            for source in result['sources']:
                print(f"  - {source['source']}")
    elif args.interactive:
        # Interactive mode
        print("\n" + "=" * 80)
        print("MTG DRAFT COACH - Interactive Mode")
        print("=" * 80)
        print("Type 'quit' to exit\n")
        
        while True:
            try:
                query = input("Your question: ").strip()
                if not query:
                    continue
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                result = rag.answer(query)
                print(f"\n{result['answer']}\n")
                
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break
    else:
        # Show system info
        info = rag.get_system_info()
        print("MTG Draft Coach RAG System")
        print(f"  Vector DB chunks: {info['vector_db']['total_chunks']}")
        print(f"  Embedding model: {info['embedding_model']['model_name']}")
        print(f"  LLM model: {info['llm_model']}")


if __name__ == "__main__":
    main()

