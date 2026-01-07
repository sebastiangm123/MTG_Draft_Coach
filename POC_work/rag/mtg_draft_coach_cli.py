#!/usr/bin/env python3
"""
MTG Draft Coach - Command Line Interface

Interactive terminal interface for the MTG Draft Coach RAG agent.
Uses all parts (1-8) from RAG_COMPONENTS_PLAN.md to answer questions.
"""

import os
import sys
from pathlib import Path
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Try pysqlite3 for ChromaDB compatibility
try:
    import pysqlite3
    import sys
    sys.modules['sqlite3'] = pysqlite3
except ImportError:
    pass

from rag.rag_orchestrator import MTGDraftCoachRAG


class MTGDraftCoachCLI:
    """Command-line interface for MTG Draft Coach RAG agent."""
    
    def __init__(
        self,
        db_path: str = "mtg_draft_coach.db",
        vector_db_path: str = "./vector_db",
        embedding_model: str = "openai",
        llm_model: str = "gpt-4"
    ):
        """Initialize CLI with RAG agent."""
        print("Initializing MTG Draft Coach RAG Agent...")
        print("=" * 80)
        
        try:
            self.rag = MTGDraftCoachRAG(
                db_path=db_path,
                vector_db_path=vector_db_path,
                embedding_model=embedding_model,
                llm_model=llm_model
            )
            print("[OK] RAG agent initialized successfully!")
            
            # Show system info
            info = self.rag.get_system_info()
            print(f"\nSystem Status:")
            print(f"  Vector DB Chunks: {info['vector_db']['total_chunks']}")
            print(f"  Embedding Model: {info['embedding_model']['model_name']}")
            print(f"  LLM Model: {info['llm_model']}")
            if not info.get('llm_available', True):
                print(f"  [WARNING] LLM not available - set OPENAI_API_KEY for AI answers")
            print(f"  Context Enabled: {info['context_enabled']}")
            print("=" * 80)
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def _ensure_vector_db_populated(self):
        """Ensure vector database has some data, populate if needed."""
        info = self.rag.get_system_info()
        if info['vector_db']['total_chunks'] == 0:
            print("\n[INFO] Vector database is empty. Populating with sample data...")
            print("This may take a moment...")
            
            # Extract and store some sample data
            from rag.mtg_draft_query_processor import MTGDraftQueryProcessor
            from rag.knowledge_base_extractor import KnowledgeBaseExtractor
            from rag.text_chunker import TextChunker
            
            processor = MTGDraftQueryProcessor(self.rag.query_processor.db_path)
            extractor = self.rag.knowledge_extractor
            chunker = self.rag.text_chunker
            
            # Get some cards and archetypes
            sample_query = processor.process("What's the best card in TLA?")
            context = extractor.extract(sample_query, max_results=10)
            
            chunks = chunker.chunk_context(context)
            if chunks:
                # Check for existing
                unique_chunk_ids = list(dict.fromkeys([chunk.chunk_id for chunk in chunks]))
                try:
                    existing = self.rag.vector_db.get_by_ids(unique_chunk_ids)
                    existing_ids = {item['id'] for item in existing}
                except Exception:
                    existing_ids = set()
                
                chunks_to_add = [chunk for chunk in chunks if chunk.chunk_id not in existing_ids]
                if chunks_to_add:
                    texts = [chunk.text for chunk in chunks_to_add]
                    embeddings = self.rag.embedding_generator.generate_batch_embeddings(
                        texts, show_progress=False
                    )
                    self.rag.vector_db.add_chunks(
                        chunk_ids=[chunk.chunk_id for chunk in chunks_to_add],
                        embeddings=embeddings,
                        texts=texts,
                        metadatas=[chunk.metadata for chunk in chunks_to_add]
                    )
                    print(f"[OK] Populated {len(chunks_to_add)} chunks into vector database")
    
    def process_query(self, query: str, show_details: bool = False):
        """Process a single query."""
        print("\n" + "=" * 80)
        print(f"Processing: {query}")
        print("=" * 80)
        
        # Ensure vector DB has data
        self._ensure_vector_db_populated()
        
        try:
            result = self.rag.answer(query, top_k=5, include_sources=True)
            
            # Show answer
            print("\n[ANSWER]")
            print("-" * 80)
            if result.get('answer'):
                print(result['answer'])
            else:
                # If no answer but we have context, show it
                if result.get('retrieval_info', {}).get('chunks_retrieved', 0) > 0:
                    print("Context retrieved but no LLM answer available.")
                    print("Set OPENAI_API_KEY to get AI-generated answers.")
                else:
                    print("No answer generated.")
            print("-" * 80)
            
            # Show details if requested
            if show_details:
                print("\n[DETAILS]")
                print("-" * 80)
                query_info = result.get('query_info', {})
                print(f"Intent: {query_info.get('intent', 'N/A')}")
                print(f"Query Type: {query_info.get('query_type', 'N/A')}")
                print(f"Confidence: {query_info.get('confidence', 0):.2f}")
                print(f"Entities: {query_info.get('entities', {})}")
                
                retrieval_info = result.get('retrieval_info', {})
                print(f"\nRetrieval:")
                print(f"  Chunks Retrieved: {retrieval_info.get('chunks_retrieved', 0)}")
                print(f"  Chunks Used: {retrieval_info.get('chunks_used', 0)}")
                print(f"  Context Length: {retrieval_info.get('context_length', 0)} chars")
                print(f"  Tokens Estimated: {retrieval_info.get('tokens_estimated', 0)}")
                
                if result.get('sources'):
                    print(f"\nSources ({len(result['sources'])}):")
                    for i, source in enumerate(result['sources'], 1):
                        print(f"  {i}. {source.get('source', 'N/A')} (distance: {source.get('distance', 'N/A'):.4f})")
                print("-" * 80)
            
            # Show error if any
            if result.get('error'):
                print(f"\n[WARNING] Error occurred: {result['error']}")
            
        except Exception as e:
            print(f"\n[ERROR] Failed to process query: {e}")
            import traceback
            traceback.print_exc()
    
    def interactive_mode(self, show_details: bool = False):
        """Run in interactive mode."""
        print("\n" + "=" * 80)
        print("MTG DRAFT COACH - Interactive Mode")
        print("=" * 80)
        print("\nAsk me anything about MTG drafting!")
        print("Type 'help' for commands, 'quit' to exit\n")
        
        while True:
            try:
                query = input("Your question: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye! Happy drafting!")
                    break
                
                if query.lower() == 'help':
                    self._show_help()
                    continue
                
                if query.lower() == 'clear':
                    self.rag.clear_conversation()
                    print("[OK] Conversation context cleared\n")
                    continue
                
                if query.lower() == 'status':
                    self._show_status()
                    continue
                
                # Process query
                self.process_query(query, show_details=show_details)
                print()  # Blank line for readability
                
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye! Happy drafting!")
                break
            except Exception as e:
                print(f"\n[ERROR] {e}\n")
    
    def _show_help(self):
        """Show help information."""
        print("\n" + "=" * 80)
        print("HELP - MTG Draft Coach Commands")
        print("=" * 80)
        print("\nCommands:")
        print("  help          - Show this help message")
        print("  status        - Show system status")
        print("  clear         - Clear conversation context")
        print("  quit / exit   - Exit the application")
        print("\nExample Questions:")
        print("  - 'p1p1 invasion submersible good?'")
        print("  - 'What does WU do in TLA?'")
        print("  - 'What should I pick at pick 5 pack 1?'")
        print("  - 'What's the win rate of Invasion Submersible?'")
        print("  - 'What direction should I draft in TLA?'")
        print("=" * 80 + "\n")
    
    def _show_status(self):
        """Show system status."""
        info = self.rag.get_system_info()
        print("\n" + "=" * 80)
        print("SYSTEM STATUS")
        print("=" * 80)
        print(f"Vector DB Chunks: {info['vector_db']['total_chunks']}")
        print(f"Embedding Model: {info['embedding_model']['model_name']}")
        print(f"Embedding Dimension: {info['embedding_model']['dimension']}")
        print(f"LLM Model: {info['llm_model']}")
        print(f"Context Enabled: {info['context_enabled']}")
        print("=" * 80 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MTG Draft Coach RAG Agent - Terminal Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python rag/mtg_draft_coach_cli.py

  # Single query
  python rag/mtg_draft_coach_cli.py --query "What's the win rate of Invasion Submersible?"

  # With details
  python rag/mtg_draft_coach_cli.py --query "p1p1 invasion submersible?" --details

  # Use local embeddings (no API key needed for embeddings)
  python rag/mtg_draft_coach_cli.py --embedding-model local
        """
    )
    
    parser.add_argument(
        '--db',
        default='mtg_draft_coach.db',
        help='Path to SQLite database (default: mtg_draft_coach.db)'
    )
    parser.add_argument(
        '--vector-db',
        default='./vector_db',
        help='Path to vector database (default: ./vector_db)'
    )
    parser.add_argument(
        '--embedding-model',
        choices=['openai', 'local'],
        default='openai',
        help='Embedding model to use (default: openai)'
    )
    parser.add_argument(
        '--llm-model',
        default='gpt-4',
        help='LLM model to use (default: gpt-4)'
    )
    parser.add_argument(
        '--query',
        help='Single query to process (if not provided, runs in interactive mode)'
    )
    parser.add_argument(
        '--details',
        action='store_true',
        help='Show detailed information (intent, entities, sources, etc.)'
    )
    
    args = parser.parse_args()
    
    # Change to POC_work directory
    os.chdir(Path(__file__).parent.parent)
    
    # Initialize CLI
    cli = MTGDraftCoachCLI(
        db_path=args.db,
        vector_db_path=args.vector_db,
        embedding_model=args.embedding_model,
        llm_model=args.llm_model
    )
    
    # Process query or run interactive mode
    if args.query:
        cli.process_query(args.query, show_details=args.details)
    else:
        cli.interactive_mode(show_details=args.details)


if __name__ == "__main__":
    main()

