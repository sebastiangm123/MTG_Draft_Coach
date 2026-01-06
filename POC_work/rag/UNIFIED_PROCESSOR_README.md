# MTG Draft Coach - Unified Query Processor

## Overview

The **MTG Draft Query Processor** is a complete, unified query processing system for the MTG Draft Coach RAG system. It combines all preprocessing, entity extraction, intent classification, and enrichment capabilities into a single, comprehensive processor.

## Features

✅ **Complete Query Processing**
- Abbreviation expansion (p1p1 → pack 1 pick 1, gih wr → games in hand win rate)
- Query normalization and rewriting
- Entity extraction (cards, archetypes, sets, picks, packs, metrics)
- Intent classification (13 intent types)
- Complexity analysis
- Ambiguity detection
- Entity validation

✅ **AI & RAG Optimization**
- AI hints generation for optimal AI model processing
- Retrieval hints for RAG system
- Query rewriting for better AI understanding
- Context-aware processing

✅ **Conversation Support**
- Follow-up query detection
- Context preservation across queries
- Elaboration handling

✅ **Multiple Input Sources**
- Terminal (interactive)
- Files (text)
- CSV (configurable)
- JSON (configurable)
- Extensible for GUI/API

## Quick Start

### Command Line

```bash
# Single query
python rag/mtg_draft_query_processor.py --query "p1p1 invasion submersible good?"

# From file
python rag/mtg_draft_query_processor.py --file queries.txt

# Interactive mode
python rag/mtg_draft_query_processor.py
```

### Python API

```python
from rag.mtg_draft_query_processor import MTGDraftQueryProcessor

# Initialize processor
processor = MTGDraftQueryProcessor("mtg_draft_coach.db", enable_context=True)

# Process query
processed = processor.process("p1p1 invasion submersible good?")

# Access all information
print(f"Original: {processed.original_query}")
print(f"Expanded: {processed.expanded_query}")
print(f"Rewritten: {processed.rewritten_query}")
print(f"Intent: {processed.intent.value}")
print(f"Type: {processed.query_type.value}")
print(f"Complexity: {processed.complexity.value}")
print(f"Entities: {processed.entities}")
print(f"AI Hints: {processed.ai_hints}")
print(f"Retrieval Hints: {processed.retrieval_hints}")
```

## Query Types Handled

### Basic Queries
- **Card Evaluation**: "Tell me about Invasion Submersible"
- **Card Comparison**: "Compare Lightning Bolt vs Counterspell"
- **Statistics**: "What's the win rate of X?"

### Drafting-Specific
- **Pick-Specific**: "What should I pick at pick 5?" or "p1p1 invasion submersible?"
- **Deck Building**: "What deck should I build?" or "How do I build a WU deck?"
- **Draft Direction**: "What direction should I draft?" or "What colors should I be in?"
- **Archetype Explanation**: "What does WU do in TLA?" or "How does the WU archetype work?"

### Follow-up & Elaboration
- **Follow-up**: "Tell me more", "What about X?"
- **Elaboration**: "Why?", "Explain that", "How does that work?"

## Abbreviation Support

The processor automatically expands common MTG abbreviations:

- `wr` → `win rate`
- `gih` → `games in hand`
- `gih wr` → `games in hand win rate`
- `p1p1` → `pack 1 pick 1`
- `p1p2` → `pack 1 pick 2`
- `cmc` → `converted mana cost`
- `md` → `maindeck`
- `sb` → `sideboard`
- `otp` → `on the play`
- `otd` → `on the draw`

## Entity Extraction

The processor extracts:

- **Cards**: Card names (with fuzzy matching)
- **Archetypes**: Color combinations (WU, URG, etc.)
- **Set Codes**: Set codes (TLA, MOM, etc.)
- **Pick Numbers**: Specific pick numbers (0-14)
- **Pack Numbers**: Specific pack numbers (0-2)
- **Draft Positions**: Position indicators (early, mid, late, first, last)
- **Metrics**: Win rate, pick number, CMC, etc.
- **Ranks**: Bronze, Silver, Gold, etc.

## AI Hints

The processor generates hints for AI models:

```python
{
    'intent': 'card_evaluation',
    'query_type': 'single_card',
    'complexity': 'simple',
    'entities_present': {
        'has_cards': True,
        'has_archetypes': False,
        'has_sets': False,
        'has_picks': False
    },
    'suggested_focus': ['card_statistics']
}
```

## Retrieval Hints

The processor generates hints for RAG retrieval:

```python
{
    'primary_entities': {
        'cards': ['invasion submersible'],
        'archetypes': [],
        'sets': []
    },
    'filters': {
        'set': None,
        'archetype': None
    },
    'expected_result_count': 3
}
```

## Conversation Context

The processor maintains conversation context:

```python
processor = MTGDraftQueryProcessor("mtg_draft_coach.db", enable_context=True)

# First query
q1 = processor.process("What's the win rate of Invasion Submersible?")
# Entities: Cards=['invasion submersible']

# Follow-up (maintains context)
q2 = processor.process("Tell me more")
# Entities: Cards=['invasion submersible'] (from context)
# Intent: FOLLOW_UP
```

## Testing

Run comprehensive tests:

```bash
# Run all tests
python rag/test_unified_processor.py

# Run specific test
python rag/test_unified_processor.py basic
python rag/test_unified_processor.py abbreviation
python rag/test_unified_processor.py pick
python rag/test_unified_processor.py followup
python rag/test_unified_processor.py comprehensive
```

## Example Output

```
Original: p1p1 invasion submersible good?
Expanded: pack 1 pick 1 invasion submersible good?
Rewritten: What is the win rate of pack 1 pick 1 invasion submersible?
Intent: card_evaluation
Type: single_card
Complexity: simple
Confidence: 0.85
Entities: Cards: ['invasion submersible']
AI Hints: {'intent': 'card_evaluation', 'query_type': 'single_card', ...}
Retrieval Hints: {'primary_entities': {'cards': ['invasion submersible'], ...}, ...}
```

## Integration with RAG

The processed query is ready for RAG integration:

```python
processed = processor.process("p1p1 invasion submersible good?")

# Use rewritten query for AI
ai_query = processed.rewritten_query

# Use retrieval hints for vector search
filters = processed.retrieval_hints['filters']
expected_count = processed.retrieval_hints['expected_result_count']

# Use AI hints for prompt construction
intent = processed.ai_hints['intent']
focus = processed.ai_hints['suggested_focus']
```

## Files

- **`mtg_draft_query_processor.py`**: Unified query processor (main file)
- **`test_unified_processor.py`**: Comprehensive test suite
- **`test_queries.txt`**: Sample queries for testing
- **`UNIFIED_PROCESSOR_README.md`**: This file

## Status

✅ **COMPLETE AND PRODUCTION-READY**

The unified query processor is fully functional and ready for integration with the RAG system. It handles all types of MTG draft-related queries and provides comprehensive preprocessing for AI models.

