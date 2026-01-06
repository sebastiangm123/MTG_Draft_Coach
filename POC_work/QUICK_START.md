# Quick Start Guide - Running the MTG Draft Pipeline

## Prerequisites

✅ You already have:
- Virtual environment set up in `POC_work/venv`
- Required dependencies installed (pandas, pyarrow, requests, tqdm)
- Parquet files ready:
  - `draft_data_public.TLA.PremierDraft.parquet`
  - `game_data_public.TLA.PremierDraft.parquet`

## Step 1: Activate Virtual Environment

**Windows PowerShell:**
```powershell
cd POC_work
.\venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**
```cmd
cd POC_work
venv\Scripts\activate.bat
```

## Step 2: Run the Pipeline

### Option A: Command Line (Recommended)

```bash
cd POC_work
python mtg_draft_pipeline.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet
```

**With custom database location:**
```bash
python mtg_draft_pipeline.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet --db my_database.db
```

**Skip Scryfall API (faster, but less complete card metadata):**
```bash
python mtg_draft_pipeline.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet --no-scryfall
```

### Option B: Python Script

```python
from mtg_draft_pipeline import MTGDraftPipeline

# Initialize pipeline
pipeline = MTGDraftPipeline(
    db_path="mtg_draft_coach.db",
    use_scryfall=True  # Set to False to skip Scryfall API
)

# Run pipeline
pipeline.run_pipeline(
    set_name="TLA",
    draft_data="draft_data_public.TLA.PremierDraft.parquet",
    game_data="game_data_public.TLA.PremierDraft.parquet"
)
```

### Option C: Use the Example Script

```bash
cd POC_work
python run_pipeline_example.py
```

(You'll need to update the file paths in `run_pipeline_example.py` first)

## What Happens

The pipeline will:

1. **Create database schema** - Sets up all 7 tables
2. **Delete existing TLA data** - Removes old data for this set (if any)
3. **Process draft data** - Extracts picks and card information
4. **Process game data** - Extracts game results and card presence
5. **Calculate statistics** - Computes win rates and metrics
6. **Create database** - Saves everything to `mtg_draft_coach.db`

**Expected time:**
- Without Scryfall: ~5-10 minutes
- With Scryfall: ~30-60 minutes (depends on number of unique cards)

## Verify It Worked

After completion, you can check the database:

```python
import sqlite3

conn = sqlite3.connect('mtg_draft_coach.db')
cursor = conn.cursor()

# Check card count
cursor.execute("SELECT COUNT(*) FROM cards WHERE set = 'TLA'")
print(f"Cards: {cursor.fetchone()[0]}")

# Check statistics count
cursor.execute("SELECT COUNT(*) FROM card_statistics WHERE set = 'TLA'")
print(f"Card Statistics: {cursor.fetchone()[0]}")

# Check archetypes
cursor.execute("SELECT COUNT(*) FROM color_archetypes WHERE set = 'TLA'")
print(f"Archetypes: {cursor.fetchone()[0]}")

conn.close()
```

## Troubleshooting

### "Module not found" error
```bash
# Make sure virtual environment is activated
# Reinstall dependencies if needed
pip install pandas pyarrow requests tqdm
```

### "File not found" error
```bash
# Make sure you're in the POC_work directory
cd POC_work
# Or use full paths
python mtg_draft_pipeline.py TLA "C:\full\path\to\draft_data.parquet" "C:\full\path\to\game_data.parquet"
```

### "set_name must be a 3-letter string" error
```bash
# Make sure set code is exactly 3 letters
python mtg_draft_pipeline.py TLA ...  # ✓ Correct
python mtg_draft_pipeline.py TheLastAirbender ...  # ✗ Wrong
```

## Next Steps

Once the pipeline completes, you'll have a SQLite database ready for your RAG agent to query!

