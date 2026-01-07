#!/usr/bin/env python3
"""
Test Knowledge Base Extractor (Part 2)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.mtg_draft_query_processor import MTGDraftQueryProcessor
from rag.knowledge_base_extractor import KnowledgeBaseExtractor


def test_card_extraction():
    """Test card extraction."""
    print("=" * 80)
    print("TEST 1: CARD EXTRACTION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    
    query = "What's the win rate of Invasion Submersible?"
    processed = processor.process(query)
    print(f"\nQuery: {query}")
    print(f"Intent: {processed.intent.value}")
    print(f"Entities: {processed.entities}")
    
    context = extractor.extract(processed, max_results=5)
    print(f"\nExtracted Context: {context}")
    print(f"Cards found: {len(context.cards)}")
    
    for card in context.cards[:3]:
        print(f"\n  Card: {card.card_name.title()}")
        print(f"    Set: {card.set}")
        print(f"    Type: {card.card_type}")
        print(f"    CMC: {card.cmc}, Colors: {card.color_identity}")
        if card.overall_wr:
            print(f"    Overall WR: {card.overall_wr * 100:.2f}%")
        if card.avg_pick:
            print(f"    Avg Pick: {card.avg_pick:.2f}")


def test_archetype_extraction():
    """Test archetype extraction."""
    print("\n" + "=" * 80)
    print("TEST 2: ARCHETYPE EXTRACTION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    
    query = "What does WU do in TLA?"
    processed = processor.process(query)
    print(f"\nQuery: {query}")
    print(f"Intent: {processed.intent.value}")
    print(f"Entities: {processed.entities}")
    
    context = extractor.extract(processed, max_results=5)
    print(f"\nExtracted Context: {context}")
    print(f"Archetypes found: {len(context.archetypes)}")
    
    for arch in context.archetypes[:3]:
        print(f"\n  Archetype: {arch.main_colors}")
        print(f"    Set: {arch.set}")
        if arch.win_rate:
            print(f"    Win Rate: {arch.win_rate * 100:.2f}%")
        if arch.total_games:
            print(f"    Total Games: {arch.total_games:,}")


def test_pick_specific_extraction():
    """Test pick-specific extraction."""
    print("\n" + "=" * 80)
    print("TEST 3: PICK-SPECIFIC EXTRACTION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    
    query = "What should I pick at pick 5 pack 1?"
    processed = processor.process(query)
    print(f"\nQuery: {query}")
    print(f"Intent: {processed.intent.value}")
    print(f"Entities: {processed.entities}")
    
    context = extractor.extract(processed, max_results=10)
    print(f"\nExtracted Context: {context}")
    print(f"Cards found: {len(context.cards)}")
    print(f"Draft Patterns found: {len(context.draft_patterns)}")
    
    if context.draft_patterns:
        print("\n  Draft Patterns:")
        for pattern in context.draft_patterns[:5]:
            print(f"    {pattern.card_name} - Pack {pattern.pack_number}, Pick {pattern.pick_number} ({pattern.count:,} times)")


def test_comparison_extraction():
    """Test card comparison extraction."""
    print("\n" + "=" * 80)
    print("TEST 4: CARD COMPARISON EXTRACTION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    
    query = "Compare Invasion Submersible vs Lightning Bolt"
    processed = processor.process(query)
    print(f"\nQuery: {query}")
    print(f"Intent: {processed.intent.value}")
    print(f"Entities: {processed.entities}")
    
    context = extractor.extract(processed, max_results=5)
    print(f"\nExtracted Context: {context}")
    print(f"Cards found: {len(context.cards)}")
    
    for card in context.cards:
        print(f"\n  {card.card_name.title()}")
        if card.overall_wr:
            print(f"    Win Rate: {card.overall_wr * 100:.2f}%")
        if card.avg_pick:
            print(f"    Avg Pick: {card.avg_pick:.2f}")


def test_general_extraction():
    """Test general extraction when no specific entities."""
    print("\n" + "=" * 80)
    print("TEST 5: GENERAL EXTRACTION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    extractor = KnowledgeBaseExtractor("mtg_draft_coach.db")
    
    query = "What's the best card in TLA?"
    processed = processor.process(query)
    print(f"\nQuery: {query}")
    print(f"Intent: {processed.intent.value}")
    print(f"Entities: {processed.entities}")
    
    context = extractor.extract(processed, max_results=5)
    print(f"\nExtracted Context: {context}")
    print(f"Cards found: {len(context.cards)}")
    
    for card in context.cards[:3]:
        print(f"\n  {card.card_name.title()}")
        if card.overall_wr:
            print(f"    Win Rate: {card.overall_wr * 100:.2f}%")


def run_all_tests():
    """Run all tests."""
    tests = [
        test_card_extraction,
        test_archetype_extraction,
        test_pick_specific_extraction,
        test_comparison_extraction,
        test_general_extraction,
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

