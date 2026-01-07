#!/usr/bin/env python3
"""
Agent Loop to Test Parts 2 and 3 Together

Tests Knowledge Base Extractor (Part 2) and Text Chunker (Part 3)
in a comprehensive loop with various query types.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.mtg_draft_query_processor import MTGDraftQueryProcessor
from rag.knowledge_base_extractor import KnowledgeBaseExtractor
from rag.text_chunker import TextChunker


class Parts2And3Tester:
    """Test agent for Parts 2 and 3."""
    
    def __init__(self, db_path: str = "mtg_draft_coach.db"):
        """Initialize tester."""
        self.processor = MTGDraftQueryProcessor(db_path)
        self.extractor = KnowledgeBaseExtractor(db_path)
        self.chunker = TextChunker()
        self.results: List[Dict[str, Any]] = []
    
    def test_query(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Test a single query through the pipeline."""
        result = {
            "query": query,
            "success": False,
            "error": None,
            "processed_query": None,
            "context": None,
            "chunks": None,
        }
        
        try:
            # Step 1: Process query
            processed = self.processor.process(query)
            result["processed_query"] = {
                "intent": processed.intent.value,
                "query_type": processed.query_type.value,
                "entities": str(processed.entities),
                "confidence": processed.confidence,
            }
            
            # Step 2: Extract context
            context = self.extractor.extract(processed, max_results=max_results)
            result["context"] = {
                "cards_count": len(context.cards),
                "archetypes_count": len(context.archetypes),
                "patterns_count": len(context.draft_patterns),
                "total_chunks": context.total_chunks,
            }
            
            # Step 3: Chunk context
            chunks = self.chunker.chunk_context(context)
            result["chunks"] = {
                "count": len(chunks),
                "types": [c.chunk_type.value for c in chunks],
                "sample_texts": [c.text[:200] for c in chunks[:2]],
            }
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
            import traceback
            result["traceback"] = traceback.format_exc()
        
        return result
    
    def run_test_suite(self):
        """Run comprehensive test suite."""
        print("=" * 80)
        print("PARTS 2 & 3 COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        
        test_queries = [
            # Card queries
            ("Card Evaluation", "What's the win rate of Invasion Submersible?"),
            ("Card with Set", "Tell me about Invasion Submersible in TLA"),
            ("Card Statistics", "What's the gih wr of invasion submersible?"),
            
            # Archetype queries
            ("Archetype Explanation", "What does WU do in TLA?"),
            ("Archetype Query", "What's the best WU deck?"),
            ("Archetype Stats", "What's the win rate of WU in TLA?"),
            
            # Pick queries
            ("Pick Specific", "What should I pick at pick 5?"),
            ("Pick with Pack", "What should I pick at pick 5 pack 1?"),
            ("P1P1", "p1p1 invasion submersible good?"),
            
            # Comparison queries
            ("Card Comparison", "Compare Invasion Submersible vs Lightning Bolt"),
            
            # General queries
            ("General", "What's the best card in TLA?"),
            ("Draft Direction", "What direction should I draft?"),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, query in test_queries:
            print(f"\n{'='*80}")
            print(f"TEST: {test_name}")
            print(f"Query: {query}")
            print(f"{'='*80}")
            
            result = self.test_query(query)
            self.results.append(result)
            
            if result["success"]:
                passed += 1
                print(f"[OK] Test passed")
                print(f"  Intent: {result['processed_query']['intent']}")
                print(f"  Entities: {result['processed_query']['entities']}")
                print(f"  Context: {result['context']['cards_count']} cards, "
                      f"{result['context']['archetypes_count']} archetypes, "
                      f"{result['context']['patterns_count']} patterns")
                print(f"  Chunks: {result['chunks']['count']} chunks")
                if result['chunks']['sample_texts']:
                    print(f"  Sample Text Preview:")
                    for i, text in enumerate(result['chunks']['sample_texts'], 1):
                        print(f"    {i}. {text[:100]}...")
            else:
                failed += 1
                print(f"[FAIL] Test failed")
                print(f"  Error: {result['error']}")
                if 'traceback' in result:
                    print(f"  Traceback: {result['traceback']}")
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {len(test_queries)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {passed/len(test_queries)*100:.1f}%")
        
        if failed == 0:
            print("\n[OK] ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {failed} test(s) failed")
        
        return failed == 0
    
    def export_results(self, output_file: str = "test_results.json"):
        """Export test results to JSON."""
        import json
        output_path = Path(__file__).parent / output_file
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nResults exported to: {output_path}")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Test Parts 2 and 3")
    parser.add_argument('--db', default='mtg_draft_coach.db', help='Database path')
    parser.add_argument('--query', help='Test single query')
    parser.add_argument('--export', help='Export results to file')
    args = parser.parse_args()
    
    os.chdir(Path(__file__).parent.parent)
    
    tester = Parts2And3Tester(args.db)
    
    if args.query:
        # Test single query
        result = tester.test_query(args.query)
        print(f"\nQuery: {args.query}")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Intent: {result['processed_query']['intent']}")
            print(f"Context: {result['context']}")
            print(f"Chunks: {result['chunks']['count']}")
            if result['chunks']['sample_texts']:
                print(f"\nSample Chunk Text:")
                print(result['chunks']['sample_texts'][0])
        else:
            print(f"Error: {result['error']}")
    else:
        # Run full test suite
        success = tester.run_test_suite()
        
        if args.export:
            tester.export_results(args.export)
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

