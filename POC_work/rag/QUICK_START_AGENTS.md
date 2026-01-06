# Quick Start: Multi-Agent Knowledge Base System

## One-Command Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key (optional - can use local embeddings)
export OPENAI_API_KEY="your-key-here"  # or use --model local

# 3. Run the full pipeline
cd POC_work/rag
python agent_orchestrator.py
```

That's it! The system will:
1. **Discover** MTG draft content locations (30 minutes)
2. **Scrape** all articles from discovered locations
3. **Process** articles into vector database

## What Gets Created

```
knowledge_base_output/
├── discovered_locations.csv      # All found locations
├── scraped_knowledge/            # Downloaded articles
│   ├── article_*.json
│   └── scraping_summary.json
├── vector_db/                    # ChromaDB database (ready for RAG!)
└── pipeline_results.json         # Full results
```

## Common Use Cases

### Use Local Embeddings (No API Key)

```bash
python agent_orchestrator.py --model local
```

### Longer Discovery Phase

```bash
# Run discovery for 60 minutes
python agent_orchestrator.py --discovery-duration 60
```

### Resume from Scraping

```bash
# Skip discovery, use existing locations.csv
python agent_orchestrator.py --skip-discovery
```

### Only Process Existing Content

```bash
# Skip discovery and scraping
python agent_orchestrator.py --skip-discovery --skip-scraping
```

## Using the Vector Database

After the pipeline completes, use the vector database:

```python
from vector_db_pipeline import VectorDBPipeline

pipeline = VectorDBPipeline(
    db_path="./knowledge_base_output/vector_db",
    embedding_model="openai"  # or "local"
)

# Search for content
results = pipeline.search("What are the best draft strategies?", n_results=5)

for result in results:
    print(f"Title: {result['metadata']['title']}")
    print(f"Source: {result['metadata']['source']}")
    print(f"Text: {result['text'][:200]}...")
```

## Troubleshooting

**Discovery finds nothing?**
- Check internet connection
- Some sites may block scrapers
- Try increasing duration: `--discovery-duration 60`

**Scraping fails?**
- Some sites may require different selectors
- Check `scraped_knowledge/scraping_summary.json` for details
- Increase delay: `--scraping-delay 2.0`

**Processing fails?**
- Check OpenAI API key if using OpenAI
- Try local embeddings: `--model local`
- Reduce batch size: `--processing-batch-size 50`

## Next Steps

1. Review `discovered_locations.csv` to see what was found
2. Check `pipeline_results.json` for statistics
3. Integrate vector database with your RAG system
4. Run periodically to keep knowledge base updated

For detailed documentation, see `AGENT_SYSTEM_README.md`.

