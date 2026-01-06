# RAG Component Architecture for MTG Draft Coach

## Overview

This document outlines all components needed to build a Retrieval-Augmented Generation (RAG) system for the MTG Draft Coach. The RAG system will enable the AI to answer questions about cards, archetypes, and draft strategy using the validated database.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUERY                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  1. QUERY PROCESSOR                                         │
│     - Parse user intent                                     │
│     - Extract entities (card names, archetypes, set codes)  │
│     - Determine query type (card, archetype, comparison)     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  2. KNOWLEDGE BASE EXTRACTOR                                │
│     - Query SQLite database                                 │
│     - Extract relevant context chunks                        │
│     - Format data for embedding                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  3. TEXT CHUNKER / DOCUMENT PREPARER                        │
│     - Split data into semantic chunks                        │
│     - Create structured text representations                 │
│     - Add metadata (card_id, set, type, etc.)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  4. EMBEDDING GENERATOR                                      │
│     - Generate embeddings for chunks                        │
│     - Use embedding model (OpenAI, local, etc.)              │
│     - Store embeddings with metadata                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  5. VECTOR DATABASE                                          │
│     - Store embeddings                                       │
│     - Enable similarity search                              │
│     - Options: ChromaDB, FAISS, Pinecone, Qdrant            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  6. RETRIEVAL SYSTEM                                         │
│     - Semantic search (vector similarity)                   │
│     - Hybrid search (vector + SQL filtering)                │
│     - Rank and filter results                               │
│     - Return top-k relevant chunks                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  7. CONTEXT ASSEMBLER                                        │
│     - Combine retrieved chunks                              │
│     - Format for LLM prompt                                 │
│     - Add metadata context                                  │
│     - Handle token limits                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  8. LLM INTEGRATION (OpenAI Chat)                           │
│     - Build prompt with context                             │
│     - Call LLM API                                          │
│     - Generate response                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    RESPONSE                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Breakdown

### 1. **Knowledge Base (Data Source)**
**Status**: ✅ **COMPLETE**

- **SQLite Database** (`mtg_draft_coach.db`)
  - 7 normalized tables with validated data
  - All tables populated and ready
  - Indexed for fast queries

**What it provides:**
- Card metadata (name, type, CMC, colors, rarity)
- Card statistics (win rates, pick numbers, usage)
- Archetype data (color combinations, win rates)
- Draft data (picks, summaries)
- Game data (results, card presence)

---

### 2. **Text Chunker / Document Preparer**
**Status**: ❌ **TO BUILD**

**Purpose**: Convert database records into text chunks suitable for embedding

**Components needed:**
- **Card Chunker**: Convert card + statistics into text
  ```python
  "Card: Invasion Submersible (TLA)
   Type: Artifact - Vehicle
   CMC: 3, Color: Blue, Rarity: Uncommon
   Opening Hand Win Rate: 61.71% (11,722 games)
   Drawn Win Rate: 63.59% (18,664 games)
   Overall Win Rate: 62.65%
   Average Pick: 2.50
   Maindeck Rate: 87.67%
   Best in: W/UG archetype (66.34% win rate)"
  ```

- **Archetype Chunker**: Convert archetype data into text
  ```python
  "Archetype: WU (White-Blue)
   Set: TLA
   Win Rate: 58.17% (33,674 games)
   Average Game Length: 9.02 turns
   Key Cards: [list of top performing cards]"
  ```

- **Draft Pattern Chunker**: Convert draft patterns into text
  ```python
  "Draft Pattern: Early Pick Blue Cards
   Cards typically picked in pack 0-1, pick 0-3
   High win rate when drafted early
   Examples: Invasion Submersible, [other cards]"
  ```

**Metadata to include:**
- `chunk_id`, `chunk_type` (card/archetype/pattern), `set`, `card_id`, `archetype_id`, `created_at`

---

### 3. **Embedding Model**
**Status**: ❌ **TO BUILD**

**Purpose**: Convert text chunks into vector embeddings

**Options:**
1. **OpenAI Embeddings** (Recommended for best quality)
   - Model: `text-embedding-3-small` or `text-embedding-3-large`
   - Pros: High quality, semantic understanding
   - Cons: API costs, rate limits

2. **Local Embeddings** (Free, self-hosted)
   - Models: `sentence-transformers/all-MiniLM-L6-v2`, `BGE-small-en-v1.5`
   - Pros: Free, no API limits, privacy
   - Cons: Lower quality, requires GPU for speed

3. **Hybrid Approach**
   - Use local for indexing, OpenAI for query embedding

**Implementation:**
```python
class EmbeddingGenerator:
    def generate_embedding(self, text: str) -> List[float]:
        # Generate embedding vector
        pass
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        # Batch processing for efficiency
        pass
```

---

### 4. **Vector Database**
**Status**: ❌ **TO BUILD**

**Purpose**: Store and search embeddings efficiently

**Options:**

1. **ChromaDB** (Recommended - Simple, Python-native)
   - Pros: Easy setup, good Python API, metadata filtering
   - Cons: In-memory by default (can persist)
   - Best for: Development and small-medium datasets

2. **FAISS** (Facebook AI Similarity Search)
   - Pros: Very fast, efficient, good for large datasets
   - Cons: More complex setup, requires manual persistence
   - Best for: Large-scale production

3. **Pinecone** (Cloud-hosted)
   - Pros: Managed service, scalable, easy to use
   - Cons: Costs money, requires internet
   - Best for: Production deployment

4. **Qdrant** (Open-source, self-hosted)
   - Pros: Fast, good filtering, can self-host
   - Cons: Requires setup
   - Best for: Production with control

**Recommended**: Start with **ChromaDB** for development, migrate to FAISS or Qdrant for production.

**Schema:**
```python
{
    "id": "chunk_123",
    "embedding": [0.123, 0.456, ...],  # Vector
    "metadata": {
        "chunk_type": "card",
        "card_id": 209,
        "card_name": "invasion submersible",
        "set": "TLA",
        "text": "Card: Invasion Submersible..."
    }
}
```

---

### 5. **Embedding Generation Pipeline**
**Status**: ❌ **TO BUILD**

**Purpose**: Generate embeddings for all database content

**Process:**
1. Query database for all cards, archetypes, etc.
2. Convert to text chunks
3. Generate embeddings in batches
4. Store in vector database with metadata

**Components:**
- `embedding_pipeline.py`: Main pipeline script
- Batch processing for efficiency
- Progress tracking
- Error handling and retry logic
- Incremental updates (only new/updated chunks)

---

### 6. **Retrieval System**
**Status**: ❌ **TO BUILD**

**Purpose**: Find relevant context for user queries

**Components:**

**A. Query Embedding**
- Convert user query to embedding
- Use same model as document embeddings

**B. Similarity Search**
- Vector similarity search (cosine similarity, dot product)
- Return top-k most similar chunks

**C. Hybrid Search** (Recommended)
- Combine vector search with SQL filtering
- Example: "Find blue cards with high win rate"
  - SQL filter: `color_identity LIKE '%U%' AND overall_wr > 0.60`
  - Vector search: Semantic similarity to query
  - Combine results

**D. Re-ranking** (Optional)
- Use cross-encoder for better ranking
- More accurate but slower

**Implementation:**
```python
class RetrievalSystem:
    def retrieve(self, query: str, top_k: int = 5, 
                 filters: Dict = None) -> List[Dict]:
        # 1. Embed query
        # 2. Vector search
        # 3. Apply filters (SQL)
        # 4. Re-rank (optional)
        # 5. Return top-k results
        pass
```

---

### 7. **Context Assembler**
**Status**: ❌ **TO BUILD**

**Purpose**: Combine retrieved chunks into LLM prompt

**Components:**
- **Chunk Selection**: Choose most relevant chunks
- **Token Management**: Stay within LLM token limits
- **Formatting**: Structure context for prompt
- **Metadata Inclusion**: Add source information

**Prompt Template:**
```
You are an expert MTG Draft Coach. Use the following data to answer questions.

CONTEXT:
[Retrieved chunk 1]
[Retrieved chunk 2]
...

USER QUESTION: {user_query}

Answer based on the context above. If the context doesn't contain enough 
information, say so.
```

---

### 8. **LLM Integration**
**Status**: ✅ **PARTIALLY COMPLETE**

**Existing**: `openai_chat.py` - Basic OpenAI interface

**Needs Enhancement:**
- Integration with context assembler
- System prompt for draft coaching
- Response formatting
- Citation/source tracking

---

### 9. **Query Processor**
**Status**: ❌ **TO BUILD**

**Purpose**: Understand user intent and extract entities

**Components:**
- **Intent Classification**: What type of question?
  - Card evaluation
  - Archetype comparison
  - Draft strategy
  - Pick advice
  
- **Entity Extraction**: Extract from query
  - Card names
  - Set codes
  - Archetypes (color combinations)
  - Metrics (win rate, pick number)

- **Query Type Detection**:
  - Single card query: "Tell me about Invasion Submersible"
  - Comparison: "Compare Lightning Bolt vs Counterspell"
  - Archetype: "What's the best WU deck?"
  - Strategy: "What should I pick first?"

**Implementation:**
```python
class QueryProcessor:
    def process(self, query: str) -> Dict:
        return {
            "intent": "card_evaluation",
            "entities": {
                "cards": ["invasion submersible"],
                "set": "TLA"
            },
            "query_type": "single_card"
        }
```

---

### 10. **RAG Orchestrator (Main Component)**
**Status**: ❌ **TO BUILD**

**Purpose**: Coordinate all components

**Flow:**
1. Receive user query
2. Process query (extract intent, entities)
3. Retrieve relevant context (vector search + SQL)
4. Assemble context into prompt
5. Call LLM with context
6. Format and return response

**Implementation:**
```python
class MTGDraftCoachRAG:
    def __init__(self, db_path, vector_db_path):
        self.query_processor = QueryProcessor()
        self.knowledge_extractor = KnowledgeExtractor(db_path)
        self.retrieval = RetrievalSystem(vector_db_path)
        self.context_assembler = ContextAssembler()
        self.llm = OpenAIChat()
    
    def answer(self, query: str) -> str:
        # Full RAG pipeline
        pass
```

---

## Data Structures for Embedding

### Card Chunk Structure
```python
{
    "chunk_id": "card_209_TLA",
    "chunk_type": "card",
    "text": "Card: Invasion Submersible (TLA)...",
    "metadata": {
        "card_id": 209,
        "card_name": "invasion submersible",
        "set": "TLA",
        "color_identity": "U",
        "cmc": 3,
        "rarity": "uncommon",
        "gih_wr": 0.6171,
        "overall_wr": 0.6265,
        "avg_pick": 2.50
    }
}
```

### Archetype Chunk Structure
```python
{
    "chunk_id": "archetype_WU_TLA",
    "chunk_type": "archetype",
    "text": "Archetype: WU (White-Blue)...",
    "metadata": {
        "archetype_id": 12,
        "main_colors": "WU",
        "set": "TLA",
        "win_rate": 0.5817,
        "total_games": 33674
    }
}
```

---

## Implementation Priority

### Phase 1: Core RAG (MVP)
1. ✅ Knowledge Base (Complete)
2. ⚠️ Text Chunker (Build)
3. ⚠️ Embedding Generator (Build)
4. ⚠️ Vector Database (Setup ChromaDB)
5. ⚠️ Retrieval System (Basic vector search)
6. ⚠️ Context Assembler (Simple)
7. ⚠️ LLM Integration (Enhance existing)
8. ⚠️ RAG Orchestrator (Build)

### Phase 2: Enhanced RAG
9. ⚠️ Query Processor (Intent + Entity extraction)
10. ⚠️ Hybrid Search (Vector + SQL)
11. ⚠️ Re-ranking (Optional)

### Phase 3: Production
12. ⚠️ Caching layer
13. ⚠️ Performance optimization
14. ⚠️ Monitoring and logging

---

## File Structure

```
POC_work/
├── rag/
│   ├── __init__.py
│   ├── chunker.py              # Text chunking
│   ├── embedding_generator.py  # Embedding generation
│   ├── vector_db.py            # Vector database interface
│   ├── retrieval.py            # Retrieval system
│   ├── context_assembler.py    # Context formatting
│   ├── query_processor.py      # Query understanding
│   ├── rag_orchestrator.py     # Main RAG class
│   └── embedding_pipeline.py   # Batch embedding generation
├── openai_chat.py              # Existing LLM interface
└── mtg_draft_coach.db          # Knowledge base
```

---

## Dependencies to Add

```python
# requirements.txt additions
chromadb>=0.4.0          # Vector database
sentence-transformers    # Local embeddings (optional)
faiss-cpu               # Alternative vector DB (optional)
openai>=1.0.0            # Already have, but ensure latest
numpy>=1.24.0            # For vector operations
```

---

## Next Steps

1. **Choose Vector Database**: Start with ChromaDB
2. **Build Text Chunker**: Convert DB records to text
3. **Set up Embedding Generator**: Choose OpenAI or local
4. **Create Embedding Pipeline**: Generate embeddings for all data
5. **Build Retrieval System**: Implement similarity search
6. **Create RAG Orchestrator**: Wire everything together
7. **Test with sample queries**: Validate end-to-end

---

## Example Usage (Target)

```python
from rag.rag_orchestrator import MTGDraftCoachRAG

# Initialize RAG system
rag = MTGDraftCoachRAG(
    db_path="mtg_draft_coach.db",
    vector_db_path="./vector_db"
)

# Answer questions
response = rag.answer("What's the best blue card in TLA?")
print(response)

response = rag.answer("Should I pick Invasion Submersible or Lightning Bolt?")
print(response)

response = rag.answer("What's the win rate of WU archetype?")
print(response)
```

---

## Key Design Decisions

1. **Hybrid Search**: Use both vector similarity AND SQL filtering for best results
2. **Chunking Strategy**: One chunk per card/archetype (simple, effective)
3. **Embedding Model**: Start with OpenAI for quality, can add local later
4. **Vector DB**: ChromaDB for simplicity, can migrate to FAISS/Qdrant later
5. **Metadata**: Store rich metadata for filtering and citation

---

This architecture provides a complete RAG system that can answer questions about MTG draft strategy using your validated database!

