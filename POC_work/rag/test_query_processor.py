#!/usr/bin/env python3
"""
Test script for Query Processor
Demonstrates usage with various query types.
"""

from query_processor import (
    QueryProcessor,
    QueryProcessorInterface,
    TerminalInputHandler,
    FileInputHandler,
    CSVInputHandler,
    JSONInputHandler
)

def test_single_queries():
    """Test processing individual queries."""
    print("=" * 80)
    print("TESTING SINGLE QUERIES")
    print("=" * 80)
    
    processor = QueryProcessor("mtg_draft_coach.db")
    
    test_queries = [
        "What's the win rate of Invasion Submersible?",
        "Compare Lightning Bolt vs Counterspell",
        "What's the best WU deck in TLA?",
        "Should I pick Invasion Submersible or Lightning Bolt?",
        "Tell me about blue cards with high win rates",
        "What cards are good in the WU archetype?",
        "Show me statistics for TLA set",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print("-" * 80)
        processed = processor.process(query)
        print(f"Intent: {processed.intent.value}")
        print(f"Type: {processed.query_type.value}")
        print(f"Confidence: {processed.confidence:.2f}")
        print(f"Entities: {processed.entities}")


def test_file_input():
    """Test file input handler."""
    print("\n" + "=" * 80)
    print("TESTING FILE INPUT")
    print("=" * 80)
    
    # Create a test file
    test_file = "test_queries.txt"
    with open(test_file, 'w') as f:
        f.write("# Test queries file\n")
        f.write("What's the win rate of Invasion Submersible?\n")
        f.write("Compare Lightning Bolt vs Counterspell\n")
        f.write("What's the best WU deck?\n")
    
    try:
        handler = FileInputHandler(test_file)
        interface = QueryProcessorInterface("mtg_draft_coach.db", handler)
        processed = interface.process_queries()
        print(f"\nProcessed {len(processed)} queries from file")
    finally:
        import os
        if os.path.exists(test_file):
            os.remove(test_file)


def test_csv_input():
    """Test CSV input handler."""
    print("\n" + "=" * 80)
    print("TESTING CSV INPUT")
    print("=" * 80)
    
    import csv
    import os
    
    # Create a test CSV
    test_csv = "test_queries.csv"
    with open(test_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['query', 'category'])
        writer.writeheader()
        writer.writerow({'query': "What's the win rate of Invasion Submersible?", 'category': 'card'})
        writer.writerow({'query': "Compare Lightning Bolt vs Counterspell", 'category': 'comparison'})
        writer.writerow({'query': "What's the best WU deck?", 'category': 'archetype'})
    
    try:
        handler = CSVInputHandler(test_csv, 'query')
        interface = QueryProcessorInterface("mtg_draft_coach.db", handler)
        processed = interface.process_queries()
        print(f"\nProcessed {len(processed)} queries from CSV")
    finally:
        if os.path.exists(test_csv):
            os.remove(test_csv)


def test_json_input():
    """Test JSON input handler."""
    print("\n" + "=" * 80)
    print("TESTING JSON INPUT")
    print("=" * 80)
    
    import json
    import os
    
    # Create a test JSON
    test_json = "test_queries.json"
    data = {
        "queries": [
            "What's the win rate of Invasion Submersible?",
            "Compare Lightning Bolt vs Counterspell",
            "What's the best WU deck?"
        ]
    }
    
    with open(test_json, 'w') as f:
        json.dump(data, f, indent=2)
    
    try:
        handler = JSONInputHandler(test_json, 'queries')
        interface = QueryProcessorInterface("mtg_draft_coach.db", handler)
        processed = interface.process_queries()
        print(f"\nProcessed {len(processed)} queries from JSON")
    finally:
        if os.path.exists(test_json):
            os.remove(test_json)


if __name__ == "__main__":
    import sys
    import os
    from pathlib import Path
    
    # Change to POC_work directory
    script_dir = Path(__file__).parent
    work_dir = script_dir.parent
    os.chdir(work_dir)
    
    print("Query Processor Test Suite")
    print("=" * 80)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "single":
            test_single_queries()
        elif test_type == "file":
            test_file_input()
        elif test_type == "csv":
            test_csv_input()
        elif test_type == "json":
            test_json_input()
        else:
            print(f"Unknown test type: {test_type}")
    else:
        # Run all tests
        test_single_queries()
        # test_file_input()  # Uncomment to test file input
        # test_csv_input()    # Uncomment to test CSV input
        # test_json_input()  # Uncomment to test JSON input

