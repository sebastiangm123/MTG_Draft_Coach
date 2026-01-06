# MTG Knowledge Base Builder

This directory contains scripts to build a knowledge base for the RAG system by scraping MTG articles and content from the web and storing them in a vector database.

## Overview

The knowledge base building process consists of three main steps:

1. **Scraping**: Scrape articles from major MTG content sources
2. **Processing**: Clean and chunk articles into embeddable pieces
3. **Vectorization**: Generate embeddings and store in ChromaDB

## Files

- `mtg_content_scraper.py` - Web scraper for MTG articles
- `content_processor.py` - Processes articles into chunks
- `vector_db_pipeline.py` - Generates embeddings and stores in vector DB
- `build_knowledge_base.py` - Master script that orchestrates the full pipeline

## Quick Start

### 1. Install Dependencies

```bash
pip install -r ../requirements.txt
```

### 2. Set Up OpenAI API Key (if using OpenAI embeddings)

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"

# Windows CMD
set OPENAI_API_KEY=your-api-key-here

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Run the Full Pipeline

```bash
# Full pipeline (scrape, process, vectorize)
python build_knowledge_base.py
```

This will:
- Scrape articles from all configured sources (ChannelFireball, StarCityGames, MTGGoldfish, TCGPlayer, Reddit)
- Process articles into chunks
- Generate embeddings and store in vector database

## Usage Options

### Scrape Only Specific Sources

```bash
python build_knowledge_base.py --sources channelfireball mtggoldfish
```

### Use Local Embeddings (No API Key Required)

```bash
python build_knowledge_base.py --model local
```

Note: Local embeddings use `sentence-transformers` which may be slower but doesn't require an API key.

### Skip Steps (Use Existing Data)

```bash
# Skip scraping (use existing articles.json)
python build_knowledge_base.py --skip-scrape

# Skip scraping and processing (use existing chunks.json)
python build_knowledge_base.py --skip-scrape --skip-process
```

### Customize Paths

```bash
python build_knowledge_base.py \
    --scraped-dir my_scraped_content \
    --processed-dir my_processed_content \
    --db-path ./my_vector_db
```

### Limit Articles Per Source

```bash
python build_knowledge_base.py --max-articles 50
```

## Individual Scripts

You can also run the scripts individually:

### 1. Scrape Content

```bash
python mtg_content_scraper.py
```

This creates `scraped_content/all_articles.json` with all scraped articles.

### 2. Process Articles

```bash
python content_processor.py scraped_content/all_articles.json processed_chunks.json
```

This creates `processed_chunks.json` with chunked content.

### 3. Build Vector Database

```bash
python vector_db_pipeline.py processed_chunks.json --model openai --db-path ./vector_db
```

## Content Sources

The scraper currently supports:

- **ChannelFireball** - Articles, draft guides, limited content
- **StarCityGames** - Strategy articles, limited content
- **MTGGoldfish** - Articles, format analysis
- **TCGPlayer** - Articles, limited content
- **Reddit** - r/magicTCG, r/lrcast, r/spikes top posts

## Output Structure

```
POC_work/
├── scraped_content/
│   ├── all_articles.json          # All scraped articles
│   ├── channelfireball_articles.json
│   ├── mtggoldfish_articles.json
│   └── ...
├── processed_content/
│   └── processed_chunks.json      # Processed chunks
└── vector_db/                      # ChromaDB database
    └── ...
```

## Using the Vector Database

Once built, you can use the vector database in your RAG system:

```python
from vector_db_pipeline import VectorDBPipeline

# Initialize pipeline
pipeline = VectorDBPipeline(db_path="./vector_db", embedding_model="openai")

# Search for relevant content
results = pipeline.search("What are the best draft strategies?", n_results=5)

for result in results:
    print(f"Title: {result['metadata']['title']}")
    print(f"Source: {result['metadata']['source']}")
    print(f"Text: {result['text'][:200]}...")
    print()
```

## Configuration

### Chunking Settings

Edit `content_processor.py` to adjust:
- `chunk_size`: Target chunk size in characters (default: 1000)
- `chunk_overlap`: Overlap between chunks (default: 200)

### Embedding Model

- **OpenAI** (`text-embedding-3-small`): Higher quality, requires API key, costs money
- **Local** (`all-MiniLM-L6-v2`): Free, no API needed, slightly lower quality

### Scraping Settings

Edit `mtg_content_scraper.py` to:
- Add new sources
- Adjust rate limiting (`delay` parameter)
- Modify selectors for different websites

## Troubleshooting

### Rate Limiting

If you get rate limited, increase the delay:
```python
scraper = MTGContentScraper(delay=2.0)  # Increase delay
```

### Missing Content

Some websites may have changed their HTML structure. Update selectors in `mtg_content_scraper.py` if scraping fails.

### OpenAI API Errors

- Check your API key is set correctly
- Ensure you have API credits
- Try using `--model local` as an alternative

### ChromaDB Errors

- Ensure the directory is writable
- Delete the vector_db directory and rebuild if corrupted

## Next Steps

After building the knowledge base:

1. Integrate with your RAG orchestrator (see `RAG_COMPONENTS_PLAN.md`)
2. Test retrieval quality with sample queries
3. Fine-tune chunking and embedding settings
4. Add more content sources as needed

## Notes

- The scraper respects rate limits with delays between requests
- Some websites may block scrapers - adjust User-Agent if needed
- Reddit scraping may be limited by Reddit's API policies
- Consider using official APIs when available (e.g., Reddit API)

