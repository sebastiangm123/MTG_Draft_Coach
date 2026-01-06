# Quick Start: Processing Large CSV Files

## TL;DR - Best Practices

1. **Use streaming** - Never load entire file into memory
2. **Process in chunks** - Batch operations (100-1000 records)
3. **Parallel I/O** - Use threading for API calls (5-10 workers)
4. **Track progress** - Enable resume with checkpoints
5. **Optimize database** - WAL mode, batch commits, increased cache

## Which Implementation to Use?

### Use `17lands_scraper.py` (Original) if:
- Learning/understanding the code
- Processing small files (< 50MB)
- Don't need resume capability
- Simple use case

### Use `17lands_scraper_optimized.py` (Optimized) if:
- Processing large files (200MB+)
- Need to resume if interrupted
- Want faster processing with parallel API calls
- Production use case

## Key Optimizations in Optimized Version

1. **WAL Mode**: Faster database writes
2. **Threading**: Parallel API calls (5x faster for API-bound operations)
3. **Checkpoints**: Resume from interruption
4. **Better Error Handling**: Skips bad rows, continues processing
5. **Progress Tracking**: See exactly where you are

## Performance Comparison

| Metric | Original | Optimized |
|--------|----------|-----------|
| API Calls | Sequential | Parallel (5 workers) |
| Database | Standard | WAL mode + optimizations |
| Resume | No | Yes (checkpoints) |
| Error Handling | Basic | Robust |
| Speed (API-bound) | ~1 card/sec | ~5 cards/sec |

## Quick Usage

```python
# Optimized version (recommended for large files)
from 17lands_scraper_optimized import OptimizedDraftDataProcessor

processor = OptimizedDraftDataProcessor("draft_data.db", max_workers=5)
processor.process_csv_file_optimized(
    "draft_data_public.TLA.PremierDraft.csv",
    chunk_size=50,
    batch_size=100,
    resume=True
)
processor.close()
```

## Memory Usage

Both implementations are memory-efficient:
- **Original**: ~50-100MB for unique cards set
- **Optimized**: ~50-100MB + thread overhead (~10MB)

For a 200MB CSV with ~500 unique cards, both use < 200MB total memory.

## Troubleshooting

**Problem**: Process is slow
- **Solution**: Increase `max_workers` (but respect API rate limits)

**Problem**: Process crashed, need to restart
- **Solution**: Use `resume=True` - it will continue from checkpoint

**Problem**: Out of memory
- **Solution**: Reduce `chunk_size` or process file in parts

**Problem**: Too many API errors
- **Solution**: Reduce `max_workers`, add more delay between requests

