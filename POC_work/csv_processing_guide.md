# Best Practices for Processing Large CSV Files

## Summary

For processing large CSV files (200MB+), the key principles are:
1. **Never load entire file into memory** - Use streaming
2. **Process in chunks** - Batch operations for efficiency
3. **Handle errors gracefully** - Skip bad rows, don't fail entire process
4. **Track progress** - Know where you are and enable resume
5. **Optimize I/O** - Batch database writes, parallel API calls

## Current Approach (Good Practices Already in Place)

1. ✅ **Streaming with csv.DictReader** - Doesn't load entire file into memory
2. ✅ **Batch inserts** - Groups database operations for efficiency
3. ✅ **Two-pass processing** - Separates data collection from API calls

## Recommended Optimizations

### 1. **Memory Management**
- Use generators/yield for large datasets
- Process in chunks and clear memory between chunks
- Use `del` to explicitly free memory for large objects
- Avoid storing entire dataset in memory (use sets/dicts for unique values only)

### 2. **Database Optimization**
- **WAL Mode**: `PRAGMA journal_mode = WAL` - Better concurrency, faster writes
- **Batch Commits**: Commit every N records, not every record
- **Prepared Statements**: Use `executemany()` for bulk inserts
- **Cache Size**: Increase SQLite cache for better performance
- **Disable Autocommit**: Control transaction boundaries manually

### 3. **Progress Tracking**
- Use `tqdm` for progress bars (optional but helpful)
- Log progress to file for long-running processes
- Estimate time remaining based on processing rate
- Show meaningful metrics (rows processed, records inserted, etc.)

### 4. **Error Handling**
- Skip bad rows instead of failing entire process
- Log errors for later review
- Implement resume capability (checkpoint system)
- Use `errors='replace'` for encoding issues

### 5. **Performance Options**
- **Pandas with chunking**: Good for data transformations, filtering
- **Multiprocessing**: For CPU-bound operations
- **Threading/Async**: For I/O-bound operations (API calls) - **Recommended for your use case**
- **Memory mapping**: For very large files with random access needs

### 6. **File Handling**
- Use buffered I/O (default in Python)
- Consider compression (gzip) if files are compressed
- Use appropriate encoding (UTF-8 with error handling)
- Use `errors='replace'` or `errors='ignore'` for problematic characters

## Comparison of Approaches

| Approach | Best For | Memory Usage | Speed | Complexity |
|----------|----------|--------------|-------|------------|
| csv.DictReader | Simple processing, streaming | Low | Medium | Low |
| pandas.read_csv(chunksize) | Data transformations, filtering | Medium | Fast | Medium |
| Dask | Very large files, distributed | Low | Very Fast | High |
| Memory mapping | Random access needed | Very Low | Fast | Medium |
| **Optimized (current)** | **API calls + DB inserts** | **Low** | **Fast** | **Medium** |

## Recommended Implementation Strategy

For your use case (200MB+ CSV with API calls):

### Phase 1: Data Collection (Current - Good!)
1. ✅ Use `csv.DictReader` to stream through file
2. ✅ Collect unique cards in a set (memory efficient)
3. ✅ Handle errors gracefully

### Phase 2: API Calls & Database (Optimized Version)
1. **Parallel API Calls**: Use `ThreadPoolExecutor` for concurrent Scryfall requests
   - 5-10 workers is usually optimal (respects rate limits)
   - Thread-safe caching to avoid duplicate requests
2. **Batch Database Inserts**: Insert 100-1000 records per transaction
3. **Progress Tracking**: Show progress with meaningful metrics
4. **Checkpoint System**: Save progress periodically to resume if interrupted
5. **Database Optimizations**: WAL mode, increased cache, batch commits

### Phase 3: Error Recovery
- Checkpoint file tracks processed cards
- Resume from last checkpoint if process is interrupted
- Log failed cards for manual review

## Implementation Files

- **`17lands_scraper.py`**: Original implementation (good for learning)
- **`17lands_scraper_optimized.py`**: Optimized version with all best practices

## Usage Example

```python
from 17lands_scraper_optimized import OptimizedDraftDataProcessor

processor = OptimizedDraftDataProcessor(
    db_path="draft_data.db",
    max_workers=5  # Parallel API calls
)

processor.process_csv_file_optimized(
    csv_file="draft_data_public.TLA.PremierDraft.csv",
    chunk_size=50,      # Fetch 50 cards in parallel
    batch_size=100,      # Insert 100 records per transaction
    resume=True          # Resume from checkpoint if interrupted
)
```

## Performance Tips

1. **Start with smaller chunk_size** (10-20) to test, then increase
2. **Monitor API rate limits** - Scryfall is generous but be respectful
3. **Use checkpoint system** for long-running processes
4. **Increase SQLite cache** if you have available RAM
5. **Process during off-peak hours** if running on shared resources

