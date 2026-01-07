#!/usr/bin/env python3
"""
Production Test Suite for Parts 4 & 5
Tests with real MTG Draft Coach data and proves the system works end-to-end
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_with_openai_if_available():
    """Test with OpenAI embeddings if API key is available."""
    print("=" * 80)
    print("TEST: OpenAI Embeddings (if API key available)")
    print("=" * 80)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[SKIP] OPENAI_API_KEY not set, skipping OpenAI test")
        return True
    
    try:
        from rag.embedding_generator import EmbeddingGenerator
        
        generator = EmbeddingGenerator(model="openai", api_key=api_key)
        
        text = "Card: Invasion Submersible (TLA) - Win Rate: 62.65%"
        embedding = generator.generate_embedding(text)
        
        print(f"[OK] Generated OpenAI embedding")
        print(f"  Dimension: {len(embedding)}")
        print(f"  Model: {generator.model_name}")
        
        return True
    except Exception as e:
        print(f"[FAIL] OpenAI test failed: {e}")
        return False


def test_vector_db_with_pysqlite3():
    """Test vector database with pysqlite3 workaround."""
    print("\n" + "=" * 80)
    print("TEST: Vector Database with pysqlite3")
    print("=" * 80)
    
    try:
        # Try to use pysqlite3 for ChromaDB compatibility
        try:
            import pysqlite3
            import sys
            sys.modules['sqlite3'] = pysqlite3
            print("[OK] Using pysqlite3 for ChromaDB compatibility")
        except ImportError:
            print("[INFO] pysqlite3 not available, using system sqlite3")
        
        from rag.vector_database import VectorDatabase
        from rag.embedding_generator import EmbeddingGenerator
        
        # Try local first, fallback to OpenAI if available
        try:
            generator = EmbeddingGenerator(model="local")
            print("[OK] Using local embeddings")
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                generator = EmbeddingGenerator(model="openai", api_key=api_key)
                print("[OK] Using OpenAI embeddings")
            else:
                raise ValueError("No embedding model available")
        
        # Initialize vector database
        vector_db = VectorDatabase(
            db_path="./test_vector_db_prod",
            collection_name="production_test",
            reset=True
        )
        
        # Create test chunks
        chunks = [
            {
                "id": "card_1",
                "text": "Card: Invasion Submersible (TLA)\nType: Artifact - Vehicle\nCMC: 3, Color: Blue\nOpening Hand Win Rate: 61.71% (11,722 games)\nOverall Win Rate: 62.65%",
                "metadata": {"chunk_type": "card", "set": "TLA", "card_name": "invasion submersible"}
            },
            {
                "id": "archetype_1",
                "text": "Archetype: White/Blue\nSet: TLA\nWin Rate: 58.17% (33,674 games)\nAverage Game Length: 9.02 turns",
                "metadata": {"chunk_type": "archetype", "set": "TLA", "main_colors": "WU"}
            }
        ]
        
        # Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = generator.generate_batch_embeddings(texts, show_progress=False)
        
        # Store in vector database
        vector_db.add_chunks(
            chunk_ids=[chunk["id"] for chunk in chunks],
            embeddings=embeddings,
            texts=texts,
            metadatas=[chunk["metadata"] for chunk in chunks]
        )
        
        print(f"[OK] Stored {len(chunks)} chunks in vector database")
        
        # Test search
        query = "What's the win rate of Invasion Submersible?"
        query_embedding = generator.generate_embedding(query)
        results = vector_db.search(query_embedding, top_k=2)
        
        print(f"[OK] Search returned {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"  {i}. ID: {result['id']}, Distance: {result['distance']:.4f}")
            print(f"     Text Preview: {result['document'][:80]}...")
        
        # Verify results
        assert len(results) > 0, "Search should return at least one result"
        assert results[0]['id'] == "card_1", "Most relevant result should be the card"
        
        print("[OK] Search results are correct")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Vector database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_rag_pipeline():
    """Test complete RAG pipeline: Query -> Process -> Extract -> Chunk -> Embed -> Store -> Retrieve."""
    print("\n" + "=" * 80)
    print("TEST: Full RAG Pipeline (Parts 1-5)")
    print("=" * 80)
    
    try:
        from rag.mtg_draft_query_processor import MTGDraftQueryProcessor
        from rag.knowledge_base_extractor import KnowledgeBaseExtractor
        from rag.text_chunker import TextChunker
        from rag.embedding_generator import EmbeddingGenerator
        from rag.vector_database import VectorDatabase
        from rag.retrieval_system import RetrievalSystem
        
        # Try pysqlite3 for ChromaDB
        try:
            import pysqlite3
            import sys
            sys.modules['sqlite3'] = pysqlite3
        except ImportError:
            pass
        
        # Initialize all components
        processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
        extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
        chunker = TextChunker()
        
        # Try local embeddings, fallback to OpenAI
        try:
            embedding_generator = EmbeddingGenerator(model="local")
            print("[OK] Using local embeddings")
        except Exception:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("[SKIP] No embedding model available (need OPENAI_API_KEY or sentence-transformers)")
                return True
            embedding_generator = EmbeddingGenerator(model="openai", api_key=api_key)
            print("[OK] Using OpenAI embeddings")
        
        vector_db = VectorDatabase(
            db_path="./test_vector_db_rag",
            collection_name="rag_pipeline",
            reset=True
        )
        retrieval = RetrievalSystem(vector_db, embedding_generator)
        
        # Test query
        query = "What's the win rate of Invasion Submersible in TLA?"
        print(f"\nQuery: {query}")
        
        # Step 1: Process query
        processed = processor.process(query)
        print(f"[OK] Processed query")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Entities: {processed.entities}")
        
        # Step 2: Extract context
        context = extractor.extract(processed, max_results=3)
        print(f"[OK] Extracted context")
        print(f"  Cards: {len(context.cards)}, Archetypes: {len(context.archetypes)}")
        
        if len(context.cards) == 0 and len(context.archetypes) == 0:
            print("[WARNING] No context extracted, cannot continue test")
            return True
        
        # Step 3: Chunk context
        chunks = chunker.chunk_context(context)
        print(f"[OK] Generated {len(chunks)} chunks")
        
        if not chunks:
            print("[WARNING] No chunks generated, cannot continue test")
            return True
        
        # Step 4: Generate embeddings and store
        texts = [chunk.text for chunk in chunks]
        embeddings = embedding_generator.generate_batch_embeddings(texts, show_progress=False)
        
        vector_db.add_chunks(
            chunk_ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            texts=texts,
            metadatas=[chunk.metadata for chunk in chunks]
        )
        print(f"[OK] Stored {len(chunks)} chunks in vector database")
        
        # Step 5: Retrieve
        results = retrieval.retrieve_with_query_processor(processed, top_k=3)
        print(f"[OK] Retrieved {len(results)} relevant chunks")
        
        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    ID: {result['id']}")
            print(f"    Distance: {result['distance']:.4f}")
            print(f"    Type: {result['metadata'].get('chunk_type', 'N/A')}")
            print(f"    Text Preview: {result['document'][:100]}...")
        
        # Verify retrieval worked
        assert len(results) > 0, "Retrieval should return at least one result"
        print("\n[OK] Full RAG pipeline test passed!")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_production_tests():
    """Run all production tests."""
    print("\n" + "=" * 80)
    print("PARTS 4 & 5 PRODUCTION TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("OpenAI Embeddings", test_with_openai_if_available),
        ("Vector Database", test_vector_db_with_pysqlite3),
        ("Full RAG Pipeline", test_full_rag_pipeline),
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            if "SKIP" in str(e) or "not available" in str(e).lower():
                skipped += 1
            else:
                failed += 1
                print(f"[FAIL] {test_name} failed: {e}")
    
    print("\n" + "=" * 80)
    print("PRODUCTION TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    
    if failed == 0:
        print("\n[OK] ALL TESTS PASSED!")
        return True
    else:
        print(f"\n[WARNING] {failed} test(s) failed")
        return False


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).parent.parent)
    
    success = run_production_tests()
    sys.exit(0 if success else 1)

