# RAG Components - Query Processor

## Overview

The Query Processor is the first component of the RAG system. It parses user queries to extract:
- **Intent**: What the user wants (card evaluation, comparison, archetype query, etc.)
- **Entities**: Card names, archetypes, set codes, metrics
- **Query Type**: Single card, comparison, archetype, strategy, etc.

## Features

- ✅ **Multiple Input Sources**: Terminal, files, CSV, JSON
- ✅ **Object-Oriented Design**: Extensible and maintainable
- ✅ **Entity Extraction**: Automatically finds cards, archetypes, sets
- ✅ **Intent Classification**: Understands user intent
- ✅ **Flexible Architecture**: Easy to add new input handlers (GUI, API, etc.)

## Installation

No additional dependencies required - uses only standard library and existing database.

## Usage

### Command Line

#### Interactive Terminal Mode
```bash
cd POC_work
python rag/query_processor.py
```

#### Single Query
```bash
python rag/query_processor.py --query "What's the win rate of Invasion Submersible?"
```

#### From Text File
```bash
# Create queries.txt with one query per line
python rag/query_processor.py --file queries.txt
```

#### From CSV File
```bash
# Create queries.csv with a 'query' column
python rag/query_processor.py --csv queries.csv --csv-column query
```

#### From JSON File
```bash
# Create queries.json with queries array
python rag/query_processor.py --json queries.json --json-key queries
```

### Python API

#### Basic Usage
```python
from rag.query_processor import QueryProcessor

processor = QueryProcessor("mtg_draft_coach.db")
processed = processor.process("What's the win rate of Invasion Submersible?")

print(f"Intent: {processed.intent.value}")
print(f"Type: {processed.query_type.value}")
print(f"Cards: {processed.entities.cards}")
print(f"Sets: {processed.entities.set_codes}")
```

#### Multiple Input Sources
```python
from rag.query_processor import (
    QueryProcessorInterface,
    TerminalInputHandler,
    FileInputHandler,
    CSVInputHandler
)

# Terminal input
interface = QueryProcessorInterface("mtg_draft_coach.db")
processed_queries = interface.process_queries()

# File input
handler = FileInputHandler("queries.txt")
interface.set_input_handler(handler)
processed_queries = interface.process_queries()

# CSV input
handler = CSVInputHandler("queries.csv", query_column="query")
interface.set_input_handler(handler)
processed_queries = interface.process_queries()
```

## Query Types

The processor recognizes many query types:

### Basic Queries
1. **Card Evaluation**: "Tell me about Invasion Submersible"
2. **Card Comparison**: "Compare Lightning Bolt vs Counterspell"
3. **Archetype Query**: "What's the best WU deck?"
4. **Draft Strategy**: "What should I pick first?"
5. **Pick Advice**: "Should I pick X or Y?"
6. **Statistics Query**: "What's the win rate of X?"

### Drafting-Specific Queries
7. **Pick-Specific**: "What should I pick at pick 5?" or "What's good for pick 1 pack 2?"
8. **Deck Building**: "What deck should I build?" or "How do I build a WU deck?"
9. **Draft Direction**: "What direction should I draft?" or "What colors should I be in?"
10. **Archetype Explanation**: "What does WU do in TLA?" or "How does the WU archetype work?"

### Follow-up Queries
11. **Follow-up**: "Tell me more", "What about X?", "And Y?"
12. **Elaboration**: "Why?", "Explain that", "How does that work?"

## Extracted Entities

The processor extracts:

- **Cards**: Card names from the database (with fuzzy matching)
- **Archetypes**: Color combinations (WU, URG, etc.)
- **Set Codes**: Set codes (TLA, MOM, etc.)
- **Pick Numbers**: Specific pick numbers (0-14)
- **Pack Numbers**: Specific pack numbers (0-2, converted from 1-3)
- **Draft Positions**: Position indicators (early, mid, late, first, last)
- **Metrics**: Win rate, pick number, CMC, etc.
- **Ranks**: Bronze, Silver, Gold, etc.
- **Event Types**: PremierDraft, QuickDraft, etc.

## Conversation Context

The enhanced query processor supports **conversation context tracking**:

- **Follow-up Detection**: Automatically detects follow-up queries
- **Context Preservation**: Maintains entities from previous queries
- **Elaboration Support**: Understands "why", "how", "explain" queries
- **Multi-turn Conversations**: Tracks up to 10 previous queries

### Example Conversation

```python
from rag.query_processor import QueryProcessor

processor = QueryProcessor("mtg_draft_coach.db", enable_context=True)

# First query
q1 = processor.process("What's the win rate of Invasion Submersible?")
# Returns: Intent=CARD_EVALUATION, Cards=['invasion submersible']

# Follow-up (maintains context)
q2 = processor.process("Tell me more")
# Returns: Intent=FOLLOW_UP, Cards=['invasion submersible'] (from context)

# Elaboration
q3 = processor.process("Why is that?")
# Returns: Intent=ELABORATION, Cards=['invasion submersible'] (from context)
```

## Architecture

### Input Handlers

All input handlers inherit from `InputHandler`:

- `TerminalInputHandler`: Interactive terminal input
- `FileInputHandler`: Text file input (one query per line)
- `CSVInputHandler`: CSV file input
- `JSONInputHandler`: JSON file input

### Adding Custom Input Handlers

```python
from rag.query_processor import InputHandler

class CustomInputHandler(InputHandler):
    def read_input(self) -> List[str]:
        # Your custom logic here
        return ["query1", "query2"]
    
    def get_source_name(self) -> str:
        return "custom_source"
```

## Example Output

```
Query: What's the win rate of Invasion Submersible in TLA?
  Intent: card_evaluation
  Type: single_card
  Confidence: 0.70
  Entities:
    Cards: ['invasion submersible']
    Sets: ['TLA']
    Metrics: ['win_rate']
```

## Testing

Run the test suite:

```bash
cd POC_work
python rag/test_query_processor.py single
```

Run enhanced query tests:

```bash
# Test pick-specific queries
python rag/test_enhanced_queries.py pick

# Test deck building queries
python rag/test_enhanced_queries.py deck

# Test follow-up queries
python rag/test_enhanced_queries.py followup

# Test complex scenarios
python rag/test_enhanced_queries.py complex

# Test robustness
python rag/test_enhanced_queries.py robust
```

## Enhanced Features

### 1. Pick-Specific Queries
Handles queries about specific draft positions:
- "What should I pick at pick 5?"
- "What's good for pick 1 pack 2?"
- "Best card at early pick?"

### 2. Deck Building Queries
Understands deck construction questions:
- "What deck should I build?"
- "How do I build a WU deck?"
- "What's a good deck list?"

### 3. Draft Direction Queries
Recognizes questions about draft strategy:
- "What direction should I draft?"
- "What colors should I be in?"
- "Should I commit to blue?"

### 4. Archetype Explanation
Handles questions about how archetypes work:
- "What does WU do in TLA?"
- "How does the WU archetype work?"
- "Explain the WU deck"

### 5. Follow-up & Elaboration
Maintains conversation context:
- "Tell me more" (follows previous query)
- "Why is that?" (elaborates on previous answer)
- "What about X?" (adds to previous context)

### 6. Robustness
- Error handling for malformed queries
- Graceful degradation on errors
- Handles edge cases (empty queries, invalid numbers, etc.)

## Next Steps

The Query Processor is designed to work with:
- **Knowledge Base Extractor** (Component 2): Uses extracted entities to query database
- **Retrieval System** (Component 6): Uses intent and entities for semantic search
- **RAG Orchestrator** (Component 10): Coordinates all components

## Design Decisions

1. **Database Integration**: Loads card names from database for accurate matching
2. **Fuzzy Matching**: Uses word-based matching to find cards even with typos
3. **Confidence Scoring**: Provides confidence scores for downstream components
4. **Extensible**: Easy to add new input handlers, intents, or entity types

