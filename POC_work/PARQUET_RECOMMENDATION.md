# Recommendation: Use Parquet for Large CSV Files

## Executive Summary

**Yes, converting to Parquet is the better approach** for your use case. Here's why and how.

## Why Parquet is Better

### 1. **Massive File Size Reduction**
- Your 200MB CSV → ~20-40MB Parquet
- **5-10x smaller** = faster I/O, less disk space

### 2. **10-20x Faster Queries**
- Columnar format: Only reads columns you need
- Your CSV has 709 columns, but you only need a few!
- Example: Query `card_name` and `gih_wr` - only reads 2 columns, not 709

### 3. **Better Memory Efficiency**
- Can process in chunks more efficiently
- Only loads what you need into memory

### 4. **Type Preservation**
- No string parsing overhead
- Integers stay integers, floats stay floats

## Recommended Workflow

### Option 1: Parquet Only (Simplest)
```
CSV → Parquet → Query Parquet directly
```

**Pros:**
- Simple workflow
- Fastest for analytical queries
- Smallest file size

**Cons:**
- Need to learn Parquet API
- Less flexible than SQL

### Option 2: Hybrid (Best of Both Worlds) ⭐ **RECOMMENDED**
```
CSV → Parquet (analytical queries) + SQLite (normalized, indexed)
```

**Pros:**
- Parquet for fast analytics
- SQLite for complex queries, joins, indexing
- Best performance for both use cases

**Cons:**
- Slightly more complex setup

### Option 3: Parquet → SQLite (Current + Optimization)
```
CSV → Parquet → SQLite (faster conversion)
```

**Pros:**
- Keep your current SQLite workflow
- Faster conversion from Parquet than CSV
- Can query both formats

## Implementation Plan

### Step 1: One-Time Conversion
```python
from parquet_processor import ParquetDraftProcessor

processor = ParquetDraftProcessor()
processor.csv_to_parquet(
    "draft_data_public.TLA.PremierDraft.csv",
    "draft_data_public.TLA.PremierDraft.parquet"
)
# Takes 1-2 minutes, creates 20-40MB file
```

### Step 2: Use Parquet for Queries
```python
# Fast columnar queries
df = processor.read_parquet("draft_data.parquet", 
                           columns=['expansion', 'pick', 'rank'])
# Only reads 3 columns, not 709!

# Fast filtering
df = processor.query_cards("draft_data.parquet", 
                          card_name="Sokka",
                          expansion="TLA")
```

### Step 3: Create Normalized Dataset
```python
# Create normalized Parquet with metadata
processor.create_normalized_parquet(
    "draft_data.parquet",
    "normalized_cards.parquet"
)
```

## Performance Comparison

For a 200MB CSV with 709 columns:

| Operation | CSV | Parquet | Improvement |
|-----------|-----|---------|-------------|
| **File Size** | 200MB | 20-40MB | **5-10x smaller** |
| **Load All Data** | 5-10 sec | 1-2 sec | **5x faster** |
| **Query 1 Column** | 5-10 sec | 0.1-0.5 sec | **20x faster** |
| **Query 3 Columns** | 5-10 sec | 0.2-0.8 sec | **10x faster** |
| **Filter + Aggregate** | 10-20 sec | 0.5-1 sec | **20x faster** |
| **Memory Usage** | High | Low | **Much better** |

## When to Use Each Format

### Use **Parquet** for:
- ✅ Large files (100MB+)
- ✅ Analytical queries (filtering, aggregations)
- ✅ Reading specific columns
- ✅ **Your draft data processing**

### Use **SQLite** for:
- ✅ Complex joins
- ✅ Indexed lookups
- ✅ Normalized schema
- ✅ ACID transactions

### Use **CSV** for:
- ✅ Small files (< 10MB)
- ✅ Human-readable format
- ✅ Maximum compatibility
- ✅ One-time processing

## Recommendation

**Use Parquet as your primary format** for the draft data:

1. **Convert once**: CSV → Parquet (one-time, 1-2 minutes)
2. **Query Parquet**: Fast analytical queries
3. **Optional SQLite**: For complex normalized queries if needed

This gives you:
- 5-10x smaller files
- 10-20x faster queries
- Better memory efficiency
- Type safety

## Migration Path

1. **Phase 1**: Convert CSV to Parquet (keep CSV as backup)
2. **Phase 2**: Update code to use Parquet for queries
3. **Phase 3**: Optionally create SQLite from Parquet (faster than from CSV)

## Code Examples

See `parquet_processor.py` for full implementation with:
- CSV to Parquet conversion
- Efficient columnar queries
- Filtering and aggregations
- Normalized dataset creation

