#!/usr/bin/env python3
"""
Test script for Enhanced Query Processor
Tests drafting-specific queries, follow-ups, and complex scenarios.
"""

from query_processor import QueryProcessor, QueryProcessorInterface

def test_pick_specific_queries():
    """Test pick-specific queries."""
    print("=" * 80)
    print("TESTING PICK-SPECIFIC QUERIES")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What should I pick at pick 5?",
        "What's good for pick 1 pack 2?",
        "Best card at pick 3?",
        "What should I pick in pack 1 pick 5?",
        "Early pick cards in TLA",
        "Late pick options",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Type: {processed.query_type.value}")
        print(f"  Picks: {processed.entities.pick_numbers}")
        print(f"  Packs: {processed.entities.pack_numbers}")
        print(f"  Positions: {processed.entities.draft_positions}")


def test_deck_building_queries():
    """Test deck building queries."""
    print("\n" + "=" * 80)
    print("TESTING DECK BUILDING QUERIES")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What deck should I build?",
        "How do I build a WU deck?",
        "What's a good deck list for TLA?",
        "Which deck should I construct?",
        "Best deck to make?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Type: {processed.query_type.value}")
        print(f"  Archetypes: {processed.entities.archetypes}")
        print(f"  Sets: {processed.entities.set_codes}")


def test_draft_direction_queries():
    """Test draft direction queries."""
    print("\n" + "=" * 80)
    print("TESTING DRAFT DIRECTION QUERIES")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What direction should I draft?",
        "What colors should I be in?",
        "Which direction should I go?",
        "Should I commit to blue?",
        "What colors are open?",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Type: {processed.query_type.value}")


def test_archetype_explanation_queries():
    """Test archetype explanation queries."""
    print("\n" + "=" * 80)
    print("TESTING ARCHETYPE EXPLANATION QUERIES")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db")
    
    queries = [
        "What does WU do in TLA?",
        "How does the WU archetype work?",
        "Explain the WU deck",
        "What is the WU archetype?",
        "Describe how WU works in this set",
    ]
    
    for query in queries:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Type: {processed.query_type.value}")
        print(f"  Archetypes: {processed.entities.archetypes}")
        print(f"  Sets: {processed.entities.set_codes}")


def test_follow_up_queries():
    """Test follow-up and elaboration queries."""
    print("\n" + "=" * 80)
    print("TESTING FOLLOW-UP QUERIES")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db", enable_context=True)
    
    # First query
    print("\n--- Initial Query ---")
    query1 = "What's the win rate of Invasion Submersible in TLA?"
    processed1 = processor.process(query1)
    print(f"Query: {query1}")
    print(f"  Intent: {processed1.intent.value}")
    print(f"  Cards: {processed1.entities.cards}")
    print(f"  Sets: {processed1.entities.set_codes}")
    
    # Follow-up queries
    follow_ups = [
        "Tell me more",
        "Why is that?",
        "What about other blue cards?",
        "How does it compare to Lightning Bolt?",
        "Explain that",
    ]
    
    print("\n--- Follow-up Queries ---")
    for query in follow_ups:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Is Follow-up: {processed.is_follow_up}")
        print(f"  Cards: {processed.entities.cards}")
        print(f"  Sets: {processed.entities.set_codes}")
        print(f"  Context maintained: {len(processed.entities.cards) > 0 or len(processed.entities.set_codes) > 0}")


def test_complex_drafting_scenarios():
    """Test complex real-world drafting scenarios."""
    print("\n" + "=" * 80)
    print("TESTING COMPLEX DRAFTING SCENARIOS")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db", enable_context=True)
    
    scenarios = [
        # Scenario 1: Pick-by-pick advice
        ("What should I pick at pick 1?", "pick_specific"),
        ("What about pick 2?", "follow_up"),
        ("And pick 3?", "follow_up"),
        
        # Scenario 2: Archetype exploration
        ("What does WU do?", "archetype_explanation"),
        ("What cards are good in it?", "follow_up"),
        ("What's the win rate?", "follow_up"),
        
        # Scenario 3: Deck building
        ("I'm in pack 2, what deck should I build?", "deck_building"),
        ("What cards should I prioritize?", "follow_up"),
        ("Why?", "elaboration"),
    ]
    
    for query, expected_type in scenarios:
        processed = processor.process(query)
        print(f"\nQuery: {query}")
        print(f"  Expected Type: {expected_type}")
        print(f"  Actual Type: {processed.query_type.value}")
        print(f"  Intent: {processed.intent.value}")
        print(f"  Confidence: {processed.confidence:.2f}")


def test_robustness():
    """Test robustness with edge cases."""
    print("\n" + "=" * 80)
    print("TESTING ROBUSTNESS")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db")
    
    edge_cases = [
        "",  # Empty query
        "?",  # Just punctuation
        "asdfghjkl",  # Nonsense
        "What is the best card at pick 999?",  # Invalid pick number
        "What about pack 10?",  # Invalid pack number
        "Compare X vs Y",  # Non-existent cards
    ]
    
    for query in edge_cases:
        try:
            processed = processor.process(query)
            print(f"\nQuery: '{query}'")
            print(f"  Processed: {processed.intent.value}")
            print(f"  Confidence: {processed.confidence:.2f}")
        except Exception as e:
            print(f"\nQuery: '{query}'")
            print(f"  Error: {e}")


if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path
    
    # Change to POC_work directory
    script_dir = Path(__file__).parent
    work_dir = script_dir.parent
    os.chdir(work_dir)
    
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "pick":
            test_pick_specific_queries()
        elif test_name == "deck":
            test_deck_building_queries()
        elif test_name == "direction":
            test_draft_direction_queries()
        elif test_name == "archetype":
            test_archetype_explanation_queries()
        elif test_name == "followup":
            test_follow_up_queries()
        elif test_name == "complex":
            test_complex_drafting_scenarios()
        elif test_name == "robust":
            test_robustness()
        else:
            print(f"Unknown test: {test_name}")
    else:
        # Run all tests
        test_pick_specific_queries()
        test_deck_building_queries()
        test_draft_direction_queries()
        test_archetype_explanation_queries()
        test_follow_up_queries()
        test_complex_drafting_scenarios()
        test_robustness()

