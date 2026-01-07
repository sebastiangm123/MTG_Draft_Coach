#!/usr/bin/env python3
"""
Test Text Chunker (Part 3)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.mtg_draft_query_processor import MTGDraftQueryProcessor
from rag.knowledge_base_extractor import KnowledgeBaseExtractor
from rag.text_chunker import TextChunker


def test_card_chunking():
    """Test card chunking."""
    print("=" * 80)
    print("TEST 1: CARD CHUNKING")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    chunker = TextChunker()
    
    query = "What's the win rate of Invasion Submersible?"
    processed = processor.process(query)
    context = extractor.extract(processed, max_results=3)
    
    chunks = chunker.chunk_context(context)
    print(f"\nQuery: {query}")
    print(f"Generated {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks[:2], 1):
        print(f"\n--- Chunk {i} ---")
        print(f"ID: {chunk.chunk_id}")
        print(f"Type: {chunk.chunk_type.value}")
        print(f"Text Length: {len(chunk.text)}")
        print(f"\nText Preview:")
        print(chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text)
        print(f"\nMetadata: {chunk.metadata}")


def test_archetype_chunking():
    """Test archetype chunking."""
    print("\n" + "=" * 80)
    print("TEST 2: ARCHETYPE CHUNKING")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    chunker = TextChunker()
    
    query = "What does WU do in TLA?"
    processed = processor.process(query)
    context = extractor.extract(processed, max_results=3)
    
    chunks = chunker.chunk_context(context)
    print(f"\nQuery: {query}")
    print(f"Generated {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks[:2], 1):
        print(f"\n--- Chunk {i} ---")
        print(f"ID: {chunk.chunk_id}")
        print(f"Type: {chunk.chunk_type.value}")
        print(f"\nText:")
        print(chunk.text)
        print(f"\nMetadata: {chunk.metadata}")


def test_draft_pattern_chunking():
    """Test draft pattern chunking."""
    print("\n" + "=" * 80)
    print("TEST 3: DRAFT PATTERN CHUNKING")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    chunker = TextChunker()
    
    query = "What should I pick at pick 5 pack 1?"
    processed = processor.process(query)
    context = extractor.extract(processed, max_results=5)
    
    chunks = chunker.chunk_context(context)
    print(f"\nQuery: {query}")
    print(f"Generated {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks[:3], 1):
        print(f"\n--- Chunk {i} ---")
        print(f"ID: {chunk.chunk_id}")
        print(f"Type: {chunk.chunk_type.value}")
        print(f"\nText:")
        print(chunk.text)
        print(f"\nMetadata: {chunk.metadata}")


def test_comparison_chunking():
    """Test comparison chunking."""
    print("\n" + "=" * 80)
    print("TEST 4: COMPARISON CHUNKING")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    chunker = TextChunker()
    
    query = "Compare Invasion Submersible vs Lightning Bolt"
    processed = processor.process(query)
    context = extractor.extract(processed, max_results=5)
    
    chunks = chunker.chunk_context(context)
    print(f"\nQuery: {query}")
    print(f"Generated {len(chunks)} chunks")
    
    # Create comparison chunk
    if len(context.cards) >= 2:
        comparison_chunk = chunker.create_comparison_chunk(context.cards[:2])
        if comparison_chunk:
            print(f"\n--- Comparison Chunk ---")
            print(f"ID: {comparison_chunk.chunk_id}")
            print(f"Type: {comparison_chunk.chunk_type.value}")
            print(f"\nText:")
            print(comparison_chunk.text)
            print(f"\nMetadata: {comparison_chunk.metadata}")


def test_full_pipeline():
    """Test full pipeline: Query -> Extract -> Chunk."""
    print("\n" + "=" * 80)
    print("TEST 5: FULL PIPELINE (Query -> Extract -> Chunk)")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    chunker = TextChunker()
    
    queries = [
        "p1p1 invasion submersible good?",
        "What does WU do in TLA?",
        "What should I pick at pick 5?",
    ]
    
    for query in queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        # Process query
        processed = processor.process(query)
        print(f"Intent: {processed.intent.value}")
        print(f"Entities: {processed.entities}")
        
        # Extract context
        context = extractor.extract(processed, max_results=5)
        print(f"Extracted: {context}")
        
        # Chunk context
        chunks = chunker.chunk_context(context)
        print(f"Generated {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks[:2], 1):
            print(f"\n  Chunk {i}: {chunk.chunk_type.value}")
            print(f"    ID: {chunk.chunk_id}")
            print(f"    Text Preview: {chunk.text[:150]}...")


def run_all_tests():
    """Run all tests."""
    tests = [
        test_card_chunking,
        test_archetype_chunking,
        test_draft_pattern_chunking,
        test_comparison_chunking,
        test_full_pipeline,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ Test failed: {test.__name__}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    import os
    os.chdir(Path(__file__).parent.parent)
    run_all_tests()

