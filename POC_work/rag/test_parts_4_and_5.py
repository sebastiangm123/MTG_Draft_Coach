#!/usr/bin/env python3
"""
Comprehensive Test Suite for Parts 4 & 5
Tests Embedding Generator and Vector Database
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.embedding_generator import EmbeddingGenerator
from rag.vector_database import VectorDatabase
from rag.text_chunker import TextChunker
from rag.knowledge_base_extractor import KnowledgeBaseExtractor
from rag.mtg_draft_query_processor import MTGDraftQueryProcessor
from rag.retrieval_system import RetrievalSystem


def test_embedding_generation():
    """Test embedding generation."""
    print("=" * 80)
    print("TEST 1: EMBEDDING GENERATION")
    print("=" * 80)
    
    # Test with local model (no API key needed)
    try:
        generator = EmbeddingGenerator(model="local")
        
        # Single embedding
        text = "Card: Invasion Submersible (TLA) - Win Rate: 62.65%"
        embedding = generator.generate_embedding(text)
        print(f"\n[OK] Generated single embedding")
        print(f"  Dimension: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
        
        # Batch embeddings
        texts = [
            "Card: Invasion Submersible",
            "Archetype: WU (White-Blue)",
            "Draft Pattern: Pack 1, Pick 1"
        ]
        embeddings = generator.generate_batch_embeddings(texts, show_progress=False)
        print(f"\n[OK] Generated batch embeddings")
        print(f"  Count: {len(embeddings)}")
        print(f"  All same dimension: {all(len(e) == len(embeddings[0]) for e in embeddings)}")
        
        # Model info
        info = generator.get_model_info()
        print(f"\n[OK] Model Info: {info}")
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


def test_vector_database():
    """Test vector database operations."""
    print("\n" + "=" * 80)
    print("TEST 2: VECTOR DATABASE OPERATIONS")
    print("=" * 80)
    
    try:
        # Initialize with reset
        vector_db = VectorDatabase(
            db_path="./test_vector_db",
            collection_name="test_collection",
            reset=True
        )
        
        # Generate test embeddings
        generator = EmbeddingGenerator(model="local")
        
        chunks = [
            {
                "id": "test_1",
                "text": "Card: Invasion Submersible - Win Rate: 62.65%",
                "metadata": {"chunk_type": "card", "set": "TLA", "card_name": "invasion submersible"}
            },
            {
                "id": "test_2",
                "text": "Archetype: WU (White-Blue) - Win Rate: 58.17%",
                "metadata": {"chunk_type": "archetype", "set": "TLA", "main_colors": "WU"}
            },
            {
                "id": "test_3",
                "text": "Draft Pattern: Pack 1, Pick 1 - Best cards",
                "metadata": {"chunk_type": "draft_pattern", "set": "TLA"}
            }
        ]
        
        # Generate embeddings
        texts = [chunk["text"] for chunk in chunks]
        embeddings = generator.generate_batch_embeddings(texts, show_progress=False)
        
        # Add to vector database
        vector_db.add_chunks(
            chunk_ids=[chunk["id"] for chunk in chunks],
            embeddings=embeddings,
            texts=texts,
            metadatas=[chunk["metadata"] for chunk in chunks]
        )
        
        print(f"\n[OK] Added {len(chunks)} chunks to vector database")
        
        # Test search
        query_text = "What's the win rate of Invasion Submersible?"
        query_embedding = generator.generate_embedding(query_text)
        results = vector_db.search(query_embedding, top_k=2)
        
        print(f"\n[OK] Search returned {len(results)} results")
        for i, result in enumerate(results, 1):
            print(f"  {i}. ID: {result['id']}, Distance: {result['distance']:.4f}")
            print(f"     Text: {result['document'][:60]}...")
        
        # Test filtered search
        filtered_results = vector_db.search(
            query_embedding,
            top_k=2,
            where={"chunk_type": "card"}
        )
        print(f"\n[OK] Filtered search (cards only) returned {len(filtered_results)} results")
        
        # Test get by IDs
        retrieved = vector_db.get_by_ids(["test_1", "test_2"])
        print(f"\n[OK] Retrieved {len(retrieved)} chunks by ID")
        
        # Test count
        count = vector_db.count()
        print(f"\n[OK] Vector database contains {count} chunks")
        
        # Test collection info
        info = vector_db.get_collection_info()
        print(f"\n[OK] Collection Info: {info}")
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


def test_full_pipeline():
    """Test full pipeline: Query → Extract → Chunk → Embed → Store → Retrieve."""
    print("\n" + "=" * 80)
    print("TEST 3: FULL PIPELINE (Query -> Extract -> Chunk -> Embed -> Store -> Retrieve)")
    print("=" * 80)
    
    try:
        # Initialize components
        processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
        extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
        chunker = TextChunker()
        embedding_generator = EmbeddingGenerator(model="local")
        vector_db = VectorDatabase(
            db_path="./test_vector_db",
            collection_name="pipeline_test",
            reset=True
        )
        retrieval = RetrievalSystem(vector_db, embedding_generator)
        
        # Test query
        query = "What's the win rate of Invasion Submersible?"
        print(f"\nQuery: {query}")
        
        # Step 1: Process query
        processed = processor.process(query)
        print(f"[OK] Processed query - Intent: {processed.intent.value}")
        
        # Step 2: Extract context
        context = extractor.extract(processed, max_results=3)
        print(f"[OK] Extracted context - {len(context.cards)} cards, {len(context.archetypes)} archetypes")
        
        # Step 3: Chunk context
        chunks = chunker.chunk_context(context)
        print(f"[OK] Generated {len(chunks)} chunks")
        
        if chunks:
            # Step 4: Generate embeddings
            texts = [chunk.text for chunk in chunks]
            embeddings = embedding_generator.generate_batch_embeddings(texts, show_progress=False)
            print(f"[OK] Generated {len(embeddings)} embeddings")
            
            # Step 5: Store in vector database
            vector_db.add_chunks(
                chunk_ids=[chunk.chunk_id for chunk in chunks],
                embeddings=embeddings,
                texts=texts,
                metadatas=[chunk.metadata for chunk in chunks]
            )
            print(f"[OK] Stored {len(chunks)} chunks in vector database")
            
            # Step 6: Retrieve
            results = retrieval.retrieve(query, top_k=3)
            print(f"[OK] Retrieved {len(results)} relevant chunks")
            
            for i, result in enumerate(results, 1):
                print(f"\n  Result {i}:")
                print(f"    ID: {result['id']}")
                print(f"    Distance: {result['distance']:.4f}")
                print(f"    Text Preview: {result['document'][:100]}...")
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


def test_retrieval_with_filters():
    """Test retrieval with query processor filters."""
    print("\n" + "=" * 80)
    print("TEST 4: RETRIEVAL WITH QUERY PROCESSOR FILTERS")
    print("=" * 80)
    
    try:
        processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
        embedding_generator = EmbeddingGenerator(model="local")
        vector_db = VectorDatabase(
            db_path="./test_vector_db",
            collection_name="filter_test",
            reset=True
        )
        retrieval = RetrievalSystem(vector_db, embedding_generator)
        
        # Add some test chunks
        chunks = [
            {
                "id": "card_tla_1",
                "text": "Card: Invasion Submersible (TLA) - Win Rate: 62.65%",
                "metadata": {"chunk_type": "card", "set": "TLA", "card_name": "invasion submersible"}
            },
            {
                "id": "archetype_tla_1",
                "text": "Archetype: WU (TLA) - Win Rate: 58.17%",
                "metadata": {"chunk_type": "archetype", "set": "TLA", "main_colors": "WU"}
            },
            {
                "id": "card_mom_1",
                "text": "Card: Lightning Bolt (MOM) - Win Rate: 65.00%",
                "metadata": {"chunk_type": "card", "set": "MOM", "card_name": "lightning bolt"}
            }
        ]
        
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedding_generator.generate_batch_embeddings(texts, show_progress=False)
        
        vector_db.add_chunks(
            chunk_ids=[chunk["id"] for chunk in chunks],
            embeddings=embeddings,
            texts=texts,
            metadatas=[chunk["metadata"] for chunk in chunks]
        )
        
        # Test query with TLA filter
        query = "What cards are good in TLA?"
        processed = processor.process(query)
        results = retrieval.retrieve_with_query_processor(processed, top_k=5)
        
        print(f"\nQuery: {query}")
        print(f"[OK] Retrieved {len(results)} results with filters")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['id']} - {result['metadata'].get('set', 'N/A')}")
        
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("PARTS 4 & 5 COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_embedding_generation,
        test_vector_database,
        test_full_pipeline,
        test_retrieval_with_filters,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] Test {test.__name__} failed: {e}")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {passed/len(tests)*100:.1f}%")
    
    if failed == 0:
        print("\n[OK] ALL TESTS PASSED!")
    else:
        print(f"\n[WARNING] {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).parent.parent)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)

