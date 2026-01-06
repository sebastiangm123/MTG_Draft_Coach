# Multi-Agent Knowledge Base System

This system uses three specialized agents to automatically discover, scrape, and process MTG draft content into a vector database for RAG.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Agent 1: Discovery Agent                                   │
│  - Searches web for MTG draft content locations             │
│  - Outputs: discovered_locations.csv                        │
│  - Runs for 30 min or until 1GB file size                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent 2: Scraping Agent                                     │
│  - Downloads articles from discovered locations             │
│  - Outputs: scraped_knowledge/*.json                        │
│  - Processes all locations from CSV                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent 3: Processing Agent                                   │
│  - Processes articles into chunks                           │
│  - Generates embeddings                                      │
│  - Stores in vector database                                 │
│  - Outputs: vector_db/ (ChromaDB)                            │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set OpenAI API Key (if using OpenAI embeddings)

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
cd POC_work/rag
python agent_orchestrator.py
```

This will:
1. **Discovery Agent** (30 minutes): Find MTG draft content locations online
2. **Scraping Agent**: Download all articles from discovered locations
3. **Processing Agent**: Process articles into vector database

## Usage Options

### Use Local Embeddings (No API Key)

```bash
python agent_orchestrator.py --model local
```

### Customize Discovery Duration

```bash
# Run discovery for 60 minutes
python agent_orchestrator.py --discovery-duration 60

# Stop when CSV reaches 2GB
python agent_orchestrator.py --discovery-max-size 2.0
```

### Skip Phases (Use Existing Data)

```bash
# Skip discovery (use existing locations.csv)
python agent_orchestrator.py --skip-discovery

# Skip discovery and scraping (use existing scraped content)
python agent_orchestrator.py --skip-discovery --skip-scraping

# Only run processing
python agent_orchestrator.py --skip-discovery --skip-scraping
```

### Limit Scraping

```bash
# Only scrape first 100 articles
python agent_orchestrator.py --scraping-max-articles 100
```

## Individual Agents

You can also run agents individually:

### Discovery Agent

```bash
python agent_discovery.py --output discovered_locations.csv --duration 30
```

Options:
- `--output`: Output CSV file
- `--duration`: Run duration in minutes
- `--max-size`: Max file size in GB
- `--max-locations`: Max locations to discover

### Scraping Agent

```bash
python agent_scraper.py discovered_locations.csv --output-dir scraped_knowledge
```

Options:
- `locations_csv`: CSV file with locations
- `--output-dir`: Directory to save scraped articles
- `--delay`: Delay between requests (seconds)
- `--max-articles`: Maximum articles to scrape

### Processing Agent

```bash
python agent_processor.py --scraped-dir scraped_knowledge --db-path ./vector_db
```

Options:
- `--scraped-dir`: Directory with scraped articles
- `--db-path`: Vector database path
- `--model`: "openai" or "local"
- `--batch-size`: Batch size for embeddings

## Output Structure

```
knowledge_base_output/
├── discovered_locations.csv      # Locations found by discovery agent
├── scraped_knowledge/            # Articles downloaded by scraping agent
│   ├── article_1.json
│   ├── article_2.json
│   ├── ...
│   └── scraping_summary.json
├── vector_db/                    # ChromaDB vector database
│   └── (ChromaDB files)
├── processing_summary.json       # Processing statistics
└── pipeline_results.json         # Full pipeline results
```

## Discovery Agent Details

The discovery agent finds MTG draft content from:

1. **Known Sites**: ChannelFireball, StarCityGames, MTGGoldfish, TCGPlayer, etc.
2. **Reddit**: r/lrcast, r/magicTCG, r/spikes
3. **YouTube**: Draft guide videos
4. **Search Engines**: DuckDuckGo searches for MTG draft content

Discovery methods:
- Sitemap crawling
- Page crawling
- Search engine queries
- Reddit API
- YouTube search

## Scraping Agent Details

The scraping agent:
- Reads locations from CSV
- Downloads HTML content
- Extracts text using site-specific selectors
- Saves articles as JSON files
- Updates CSV with status (scraped/failed)

Site-specific selectors are configured for:
- ChannelFireball
- StarCityGames
- MTGGoldfish
- TCGPlayer
- Reddit
- YouTube
- Default fallback

## Processing Agent Details

The processing agent:
- Loads all scraped articles
- Chunks articles (1000 chars, 200 overlap)
- Generates embeddings (OpenAI or local)
- Stores in ChromaDB vector database

## Configuration

### Discovery Settings

Edit `agent_discovery.py` to:
- Add new known sites
- Modify search keywords
- Adjust content patterns
- Add discovery methods

### Scraping Settings

Edit `agent_scraper.py` to:
- Add site-specific selectors
- Adjust rate limiting
- Modify content extraction logic

### Processing Settings

Edit `agent_processor.py` to:
- Change chunk size/overlap
- Adjust batch sizes
- Modify embedding settings

## Monitoring Progress

The orchestrator saves progress to `pipeline_results.json`:

```json
{
  "started_at": "2024-01-01T12:00:00",
  "discovery": {
    "locations_found": 500,
    "output_file": "discovered_locations.csv",
    "file_size_mb": 15.2
  },
  "scraping": {
    "scraped": 450,
    "failed": 50,
    "output_dir": "scraped_knowledge"
  },
  "processing": {
    "articles_processed": 450,
    "chunks_created": 2500,
    "chunks_stored": 2500,
    "total_chunks_in_db": 2500
  },
  "completed_at": "2024-01-01T14:30:00",
  "success": true
}
```

## Troubleshooting

### Discovery Agent Issues

- **Rate limiting**: Increase delays in discovery methods
- **No results**: Check if sites changed structure, update selectors
- **File too large**: Reduce `--discovery-max-size` or `--max-locations`

### Scraping Agent Issues

- **Many failures**: Some sites may block scrapers, update User-Agent
- **Missing content**: Update site selectors in `agent_scraper.py`
- **Slow scraping**: Increase `--delay` to be more respectful

### Processing Agent Issues

- **OpenAI API errors**: Check API key, credits, or use `--model local`
- **Out of memory**: Reduce `--batch-size`
- **ChromaDB errors**: Delete vector_db directory and rebuild

## Best Practices

1. **Run discovery first**: Let it run for the full duration to find maximum locations
2. **Review locations**: Check `discovered_locations.csv` before scraping
3. **Respect rate limits**: Use appropriate delays (1-2 seconds)
4. **Monitor progress**: Check `pipeline_results.json` for status
5. **Incremental updates**: Skip phases to rebuild only what's needed

## Integration with RAG

Once the vector database is built, use it in your RAG system:

```python
from vector_db_pipeline import VectorDBPipeline

pipeline = VectorDBPipeline(db_path="./knowledge_base_output/vector_db", embedding_model="openai")
results = pipeline.search("What are the best draft strategies?", n_results=5)
```

## Next Steps

1. Run the full pipeline to build initial knowledge base
2. Review discovered locations and add more sources
3. Fine-tune scraping selectors for better content extraction
4. Integrate vector database with your RAG orchestrator
5. Set up periodic runs to keep knowledge base updated

