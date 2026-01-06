# Knowledge Base Building - Summary

## What Was Created

This knowledge base building system allows you to scrape Magic: The Gathering articles and content from the web, process them into chunks, and store them in a vector database for use in your RAG architecture.

## Files Created

### Core Scripts

1. **`mtg_content_scraper.py`**
   - Web scraper for MTG articles from major sources
   - Supports: ChannelFireball, StarCityGames, MTGGoldfish, TCGPlayer, Reddit
   - Respects rate limits and handles errors gracefully
   - Outputs JSON files with scraped articles

2. **`content_processor.py`**
   - Processes scraped articles into embeddable chunks
   - Cleans text and splits into appropriate sizes
   - Adds metadata to each chunk
   - Configurable chunk size and overlap

3. **`vector_db_pipeline.py`**
   - Generates embeddings using OpenAI or local models
   - Stores chunks in ChromaDB vector database
   - Provides search functionality
   - Handles batch processing for efficiency

4. **`build_knowledge_base.py`**
   - Master orchestrator script
   - Runs the full pipeline: scrape → process → vectorize
   - Command-line interface with options
   - Can skip steps to use existing data

5. **`example_usage.py`**
   - Demonstrates how to use the vector database
   - Shows search examples and filtering
   - Useful for testing and understanding the API

### Documentation

- **`KNOWLEDGE_BASE_README.md`** - Complete usage guide
- **`KNOWLEDGE_BASE_SUMMARY.md`** - This file

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set OpenAI API key (if using OpenAI embeddings)
export OPENAI_API_KEY="your-key-here"

# 3. Run the full pipeline
cd rag
python build_knowledge_base.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Web Sources (ChannelFireball, MTGGoldfish, etc.)      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  mtg_content_scraper.py                                 │
│  - Scrapes articles from websites                       │
│  - Outputs: scraped_content/all_articles.json           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  content_processor.py                                   │
│  - Cleans and chunks articles                           │
│  - Outputs: processed_content/processed_chunks.json     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  vector_db_pipeline.py                                  │
│  - Generates embeddings                                 │
│  - Stores in ChromaDB                                   │
│  - Outputs: vector_db/ (ChromaDB database)              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  RAG System                                             │
│  - Uses vector_db_pipeline.search() for retrieval       │
│  - Integrates with your RAG orchestrator                │
└─────────────────────────────────────────────────────────┘
```

## Integration with RAG System

The vector database can be integrated into your RAG system as follows:

```python
from vector_db_pipeline import VectorDBPipeline

# Initialize (use same model as when building)
pipeline = VectorDBPipeline(db_path="./vector_db", embedding_model="openai")

# In your RAG orchestrator:
def retrieve_context(query: str, top_k: int = 5):
    results = pipeline.search(query, n_results=top_k)
    
    # Format for LLM context
    context = "\n\n".join([
        f"Source: {r['metadata']['title']}\n{r['text']}"
        for r in results
    ])
    
    return context
```

## Configuration Options

### Embedding Models

- **OpenAI** (`text-embedding-3-small`): Best quality, requires API key
- **Local** (`all-MiniLM-L6-v2`): Free, no API needed, good quality

### Chunking

- Default: 1000 characters per chunk, 200 character overlap
- Adjustable in `ContentProcessor` initialization

### Sources

- Easily add new sources by updating `MTGContentScraper.sources`
- Each source needs: base_url, article_urls, selectors

## Output Structure

```
POC_work/rag/
├── scraped_content/          # Scraped articles (JSON)
│   ├── all_articles.json
│   └── {source}_articles.json
├── processed_content/        # Processed chunks (JSON)
│   └── processed_chunks.json
└── vector_db/                # ChromaDB database
    └── (ChromaDB files)
```

## Next Steps

1. **Run the pipeline** to build your initial knowledge base
2. **Test retrieval** using `example_usage.py`
3. **Integrate** with your RAG orchestrator (see `RAG_COMPONENTS_PLAN.md`)
4. **Fine-tune** chunking and embedding settings based on results
5. **Add more sources** as needed (podcasts, YouTube transcripts, etc.)

## Notes

- The scraper includes rate limiting to be respectful to websites
- Some websites may require updated selectors if their HTML changes
- Consider using official APIs when available (e.g., Reddit API)
- The vector database can be rebuilt incrementally as new content is added

## Troubleshooting

See `KNOWLEDGE_BASE_README.md` for detailed troubleshooting guide.

Common issues:
- Rate limiting: Increase delay in scraper
- Missing content: Update selectors for changed websites
- API errors: Check API key or use local embeddings
- Database errors: Delete vector_db and rebuild

