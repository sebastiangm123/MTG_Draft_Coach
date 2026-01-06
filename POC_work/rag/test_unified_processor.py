#!/usr/bin/env python3
"""
Comprehensive Test Suite for Unified MTG Draft Query Processor

Tests all aspects of query processing for MTG Draft Coach RAG system.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.mtg_draft_query_processor import MTGDraftQueryProcessor, MTGDraftQueryProcessorInterface


def test_basic_queries():
    """Test basic query types."""
    print("=" * 80)
    print("TEST 1: BASIC QUERIES")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What's the win rate of Invasion Submersible?",
        "Compare Lightning Bolt vs Counterspell",
        "What's the best WU deck?",
        "What should I pick first?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Type: {processed.query_type.value}")
        print(f"  Entities: {processed.entities}")
        print(f"  Confidence: {processed.confidence:.2f}")


def test_abbreviation_expansion():
    """Test abbreviation expansion."""
    print("\n" + "=" * 80)
    print("TEST 2: ABBREVIATION EXPANSION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What's the gih wr of invasion submersible?",
        "p1p1 invasion submersible good?",
        "What's the cmc of lightning bolt?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nOriginal: {query}")
        print(f"  Expanded: {processed.expanded_query}")
        print(f"  Rewritten: {processed.rewritten_query}")


def test_pick_specific_queries():
    """Test pick-specific queries."""
    print("\n" + "=" * 80)
    print("TEST 3: PICK-SPECIFIC QUERIES")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What should I pick at pick 5?",
        "What's good for pick 1 pack 2?",
        "Best card at pick 3?",
        "p1p1 invasion submersible?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Picks: {processed.entities.pick_numbers}")
        print(f"  Packs: {processed.entities.pack_numbers}")


def test_deck_building_queries():
    """Test deck building queries."""
    print("\n" + "=" * 80)
    print("TEST 4: DECK BUILDING QUERIES")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What deck should I build?",
        "How do I build a WU deck?",
        "What's a good deck list for TLA?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Type: {processed.query_type.value}")


def test_archetype_queries():
    """Test archetype queries."""
    print("\n" + "=" * 80)
    print("TEST 5: ARCHETYPE QUERIES")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What does WU do in TLA?",
        "How does the WU archetype work?",
        "What's the best WU deck?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Archetypes: {processed.entities.archetypes}")
        print(f"  Sets: {processed.entities.set_codes}")


def test_follow_up_queries():
    """Test follow-up queries with context."""
    print("\n" + "=" * 80)
    print("TEST 6: FOLLOW-UP QUERIES (WITH CONTEXT)")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db", enable_context=True)
    
    # Initial query
    q1 = processor.process("What's the win rate of Invasion Submersible in TLA?")
    print(f"\n[1] Query: What's the win rate of Invasion Submersible in TLA?")
    print(f"    Intent: {q1.intent.value}")
    print(f"    Cards: {q1.entities.cards}")
    print(f"    Sets: {q1.entities.set_codes}")
    
    # Follow-up queries
    follow_ups = [
        "Tell me more",
        "Why is that?",
        "What about other blue cards?",
    ]
    
    for i, query in enumerate(follow_ups, 2):
        processed = processor.process(query)
        print(f"\n[{i}] Query: {query}")
        print(f"    Intent: {processed.intent.value}")
        print(f"    Is Follow-up: {processed.is_follow_up}")
        print(f"    Cards: {processed.entities.cards}")
        print(f"    Sets: {processed.entities.set_codes}")
        print(f"    Context Maintained: {len(processed.entities.cards) > 0 or len(processed.entities.set_codes) > 0}")


def test_complexity_analysis():
    """Test complexity analysis."""
    print("\n" + "=" * 80)
    print("TEST 7: COMPLEXITY ANALYSIS")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        ("Simple", "What's the win rate of Invasion Submersible?"),
        ("Moderate", "Compare Invasion Submersible vs Lightning Bolt"),
        ("Complex", "What should I pick at pick 5 pack 1 in TLA for a WU deck?"),
    ]
    
    for name, query in queries:
        processed = processor.process(query)
        print(f"\n{name}: {query}")
        print(f"  Complexity: {processed.complexity.value}")
        print(f"  Entity Count: {len(processed.entities.cards) + len(processed.entities.archetypes)}")


def test_ai_hints():
    """Test AI hints generation."""
    print("\n" + "=" * 80)
    print("TEST 8: AI HINTS GENERATION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What's the win rate of Invasion Submersible?",
        "What's the best WU deck?",
        "What should I pick at pick 5?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  AI Hints: {processed.ai_hints}")
        print(f"  Retrieval Hints: {processed.retrieval_hints}")


def test_ambiguity_detection():
    """Test ambiguity detection."""
    print("\n" + "=" * 80)
    print("TEST 9: AMBIGUITY DETECTION")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "Is it good?",
        "What about that?",
        "Compare X and Y",  # Assuming X and Y aren't found
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Ambiguity: {processed.ambiguity.value}")
        print(f"  Requires Clarification: {processed.requires_clarification}")
        if processed.clarification_questions:
            print(f"  Clarification Questions: {processed.clarification_questions}")


def test_comprehensive_scenarios():
    """Test comprehensive real-world scenarios."""
    print("\n" + "=" * 80)
    print("TEST 10: COMPREHENSIVE REAL-WORLD SCENARIOS")
    print("=" * 80)
    
    processor = MTGDraftQueryProcessor("mtg_draft_coach.db", enable_context=True)
    
    scenarios = [
        # Scenario 1: Pick-by-pick advice
        ("What should I pick at pick 1?", "pick_specific"),
        ("What about pick 2?", "follow_up"),
        
        # Scenario 2: Card evaluation
        ("p1p1 invasion submersible good?", "pick_specific"),
        ("Tell me more", "follow_up"),
        
        # Scenario 3: Archetype exploration
        ("What does WU do in TLA?", "archetype_explanation"),
        ("What cards are good in it?", "follow_up"),
    ]
    
    for query, expected_type in scenarios:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Expected Type: {expected_type}")
        print(f"  Actual Type: {processed.query_type.value}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Complexity: {processed.complexity.value}")
        print(f"  Confidence: {processed.confidence:.2f}")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("MTG DRAFT QUERY PROCESSOR - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_basic_queries,
        test_abbreviation_expansion,
        test_pick_specific_queries,
        test_deck_building_queries,
        test_archetype_queries,
        test_follow_up_queries,
        test_complexity_analysis,
        test_ai_hints,
        test_ambiguity_detection,
        test_comprehensive_scenarios,
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
    import sys
    from pathlib import Path
    
    # Change to POC_work directory
    script_dir = Path(__file__).parent
    work_dir = script_dir.parent
    os.chdir(work_dir)
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        test_map = {
            'basic': test_basic_queries,
            'abbreviation': test_abbreviation_expansion,
            'pick': test_pick_specific_queries,
            'deck': test_deck_building_queries,
            'archetype': test_archetype_queries,
            'followup': test_follow_up_queries,
            'complexity': test_complexity_analysis,
            'ai_hints': test_ai_hints,
            'ambiguity': test_ambiguity_detection,
            'comprehensive': test_comprehensive_scenarios,
        }
        test_func = test_map.get(test_name)
        if test_func:
            test_func()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: basic, abbreviation, pick, deck, archetype, followup, complexity, ai_hints, ambiguity, comprehensive")
    else:
        run_all_tests()

