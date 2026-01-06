# MTG Draft Pipeline Usage Guide

## Overview

The `mtg_draft_pipeline.py` script processes Parquet files containing Magic: The Gathering draft and game data, and creates a normalized SQLite database optimized for RAG (Retrieval-Augmented Generation) queries.

## Features

- **Dynamic Schema Detection**: Automatically extracts card names from column prefixes
- **Set-Specific Processing**: Processes data for any MTG set
- **Complete Statistics**: Calculates opening hand win rate, drawn win rate, and overall win rate
- **RAG-Optimized**: Database schema designed for fast queries by RAG agents
- **Overwrite Support**: Can replace existing data for a set

## Requirements

```bash
pip install pandas pyarrow sqlite3 requests tqdm
```

## Usage

### Basic Usage

```bash
python mtg_draft_pipeline.py TLA draft_data.parquet game_data.parquet
```

### Command-Line Arguments

**Positional Arguments (Required):**
- `set_name`: Set code as 3-letter string (e.g., TLA, MOM, BRO)
- `draft_data`: Path to draft data Parquet file
- `game_data`: Path to game data Parquet file

**Optional Arguments:**
- `--db`: SQLite database path (default: `mtg_draft_coach.db`)
- `--no-scryfall`: Skip Scryfall API calls for card metadata (faster, less complete)

### Examples

```bash
# Basic usage
python mtg_draft_pipeline.py TLA draft_data.parquet game_data.parquet

# Custom database location
python mtg_draft_pipeline.py MOM draft_data.parquet game_data.parquet --db custom.db

# Skip Scryfall API (faster processing)
python mtg_draft_pipeline.py BRO draft_data.parquet game_data.parquet --no-scryfall
```

### Python API Usage

```python
from mtg_draft_pipeline import MTGDraftPipeline

# Initialize pipeline
pipeline = MTGDraftPipeline(
    db_path="mtg_draft_coach.db",
    use_scryfall=True  # Fetch card metadata from Scryfall (default: True)
)

# Run pipeline
pipeline.run_pipeline(
    set_name="TLA",  # 3-letter set code
    draft_data="draft_data_public.TLA.PremierDraft.parquet",
    game_data="game_data_public.TLA.PremierDraft.parquet"
)
```

**Note**: The pipeline always overwrites existing data for the specified set. If you want to keep existing data, you'll need to modify the code or use a different database file.

## How It Works

### 1. Schema Detection

The pipeline automatically detects card names from column prefixes:
- `pack_card_*` - Cards in pack
- `pool_*` - Cards in pool
- `opening_hand_*` - Cards in opening hand
- `drawn_*` - Cards drawn during game
- `tutored_*` - Cards tutored
- `deck_*` - Cards in deck
- `sideboard_*` - Cards in sideboard

### 2. Data Processing Steps

1. **Extract Card Names**: Scans Parquet file columns to find all unique card names
2. **Process Cards**: Inserts cards into database, optionally fetching metadata from Scryfall
3. **Process Draft Picks**: Extracts and stores all draft pick records
4. **Process Game Results**: Extracts game outcomes and card presence data
5. **Calculate Statistics**: Computes win rates and other metrics
6. **Calculate Archetypes**: Aggregates color combination statistics
7. **Calculate Draft Summaries**: Creates draft-level aggregations

### 3. Database Schema

The pipeline creates 7 normalized tables:

1. **cards**: Master card data (name, set, color identity, CMC, type)
2. **card_statistics**: Card performance metrics (GIH WR, drawn WR, overall WR)
3. **color_archetypes**: Color combination win rates
4. **draft_picks**: Individual pick records
5. **draft_summaries**: Draft-level aggregations
6. **game_results**: Individual game records
7. **game_cards**: Card presence in games (junction table)

## Performance Considerations

### Scryfall API

- **With Scryfall**: More complete card metadata (color identity, CMC, type) but slower
- **Without Scryfall**: Faster processing but limited metadata
- **Rate Limiting**: Built-in 0.1s delay between API calls

### Memory Usage

- Processes Parquet files in chunks (5,000-10,000 rows)
- Commits to database every 1,000 records
- Uses WAL mode for better write performance

### Processing Time

For a typical set (~100,000 picks, ~200,000 games):
- **Without Scryfall**: ~5-10 minutes
- **With Scryfall**: ~30-60 minutes (depends on number of unique cards)

## Example Queries for RAG Agent

### Get Card Win Rates

```sql
SELECT 
    c.card_name,
    cs.gih_wr AS opening_hand_wr,
    cs.drawn_wr AS drawn_wr,
    cs.overall_wr,
    cs.gih_games,
    cs.drawn_games
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE c.set = 'TLA' 
  AND c.card_name LIKE '%lightning%'
ORDER BY cs.overall_wr DESC;
```

### Get Archetype Performance

```sql
SELECT 
    main_colors,
    splash_colors,
    win_rate,
    total_games,
    total_wins
FROM color_archetypes
WHERE set = 'TLA'
ORDER BY win_rate DESC
LIMIT 10;
```

### Get Card Performance in Specific Archetype

```sql
SELECT 
    c.card_name,
    cs.gih_wr,
    cs.drawn_wr,
    cs.overall_wr
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs.set = 'TLA'
  AND EXISTS (
    SELECT 1 FROM draft_summaries ds
    WHERE ds.draft_id IN (
      SELECT draft_id FROM draft_picks WHERE card_id = c.card_id
    ) AND ds.final_colors = 'UR'
  )
ORDER BY cs.overall_wr DESC;
```

## Troubleshooting

### File Not Found

```
FileNotFoundError: Draft data file not found: ...
```

**Solution**: Ensure Parquet files exist and paths are correct (use absolute paths if needed).

### Memory Issues

If processing very large files causes memory issues:

1. Reduce batch size in code (currently 5,000-10,000)
2. Process files separately (draft first, then game)
3. Use `--no-scryfall` to reduce processing time

### Database Locked

```
sqlite3.OperationalError: database is locked
```

**Solution**: 
- Close any other connections to the database
- Wait for current process to finish
- Check for stale lock files

### Scryfall API Errors

If Scryfall API calls fail:
- Check internet connection
- API may be rate-limited (wait and retry)
- Use `--no-scryfall` to skip API calls

## Output

The pipeline creates/updates a SQLite database with:
- All cards from the set
- Complete draft pick history
- All game results
- Calculated win rate statistics
- Color archetype statistics
- Draft summaries

All data is indexed for fast RAG queries.

## Next Steps

After running the pipeline:

1. **Verify Data**: Query the database to ensure data was processed correctly
2. **Test RAG Queries**: Run example queries to verify performance
3. **Update RAG Agent**: Point your RAG agent to the SQLite database
4. **Monitor Performance**: Check query times and optimize indexes if needed

## Support

For issues or questions:
1. Check the database schema plan: `DATABASE_SCHEMA_PLAN.md`
2. Review error messages for specific issues
3. Check Parquet file structure matches expected format

