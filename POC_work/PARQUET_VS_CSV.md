# Parquet vs CSV: Which Should You Use?

## Quick Answer: **Parquet is Better for Your Use Case**

For large analytical datasets (200MB+), Parquet offers significant advantages.

## Comparison

| Feature | CSV | Parquet | Winner |
|---------|-----|---------|--------|
| **File Size** | 200MB | ~20-40MB (5-10x smaller) | 🏆 Parquet |
| **Read Speed** | Slow (parse strings) | Fast (binary, columnar) | 🏆 Parquet |
| **Write Speed** | Fast | Medium (compression overhead) | CSV |
| **Memory Usage** | High (load all) | Low (read only needed columns) | 🏆 Parquet |
| **Type Safety** | No (all strings) | Yes (preserves types) | 🏆 Parquet |
| **Schema** | No | Yes (built-in) | 🏆 Parquet |
| **Query Performance** | Slow (full scan) | Fast (columnar, predicate pushdown) | 🏆 Parquet |
| **Human Readable** | Yes | No (binary) | CSV |
| **Compatibility** | Universal | Requires library | CSV |

## Why Parquet is Better for Your Use Case

### 1. **File Size Reduction**
- Your 200MB CSV → ~20-40MB Parquet (5-10x smaller)
- Saves disk space and I/O time

### 2. **Faster Queries**
- Columnar format: Only reads columns you need
- Example: Query `card_name` and `gih_wr` - only reads those 2 columns, not all 709!
- Predicate pushdown: Filters applied before reading data

### 3. **Type Preservation**
- CSV: Everything is strings (need to parse)
- Parquet: Preserves types (integers, floats, dates)
- No parsing overhead

### 4. **Better for Analytics**
- Aggregations (SUM, AVG, COUNT) are much faster
- Filtering is optimized
- Perfect for your normalized card data queries

### 5. **Memory Efficient**
- Can read specific columns without loading entire file
- Process in chunks more efficiently

## When to Use Each

### Use **Parquet** when:
- ✅ Large files (100MB+)
- ✅ Analytical queries (filtering, aggregations)
- ✅ Need to query specific columns
- ✅ Data is read more than written
- ✅ **Your use case!**

### Use **CSV** when:
- ✅ Small files (< 10MB)
- ✅ Need human-readable format
- ✅ One-time processing
- ✅ Maximum compatibility needed
- ✅ Simple data exchange

## Performance Example

For a 200MB CSV with 709 columns:

| Operation | CSV | Parquet | Improvement |
|-----------|-----|---------|-------------|
| Load file | 5-10 sec | 1-2 sec | **5x faster** |
| Query 1 column | 5-10 sec | 0.1-0.5 sec | **20x faster** |
| Filter + aggregate | 10-20 sec | 0.5-1 sec | **20x faster** |
| File size | 200MB | 20-40MB | **5-10x smaller** |

## Implementation Strategy

### Recommended Workflow:

1. **One-time conversion**: Convert CSV → Parquet (takes 1-2 minutes)
2. **Use Parquet for all queries**: Much faster for everything
3. **Keep CSV as backup**: If needed for compatibility

### Hybrid Approach (Best of Both):

```
CSV (source) → Parquet (working format) → SQLite (normalized queries)
```

- **Parquet**: Fast analytical queries, aggregations
- **SQLite**: Complex joins, normalized schema, indexed lookups

## Conclusion

**For your draft data processing, Parquet is the clear winner.**

Benefits:
- 5-10x smaller files
- 10-20x faster queries
- Better memory efficiency
- Type safety
- Built-in schema

The one-time conversion cost is worth it for the ongoing performance gains.

