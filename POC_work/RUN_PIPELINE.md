# Run the Pipeline - Quick Command Reference

## Exact Command for Your Files

From the `POC_work` directory, run:

```bash
python mtg_draft_pipeline.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet
```

## Step-by-Step

1. **Open terminal/PowerShell**
2. **Navigate to POC_work directory:**
   ```bash
   cd C:\MTG_Draft_Coach\POC_work
   ```

3. **Activate virtual environment (if not already active):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   OR
   ```cmd
   venv\Scripts\activate.bat
   ```

4. **Run the pipeline:**
   ```bash
   python mtg_draft_pipeline.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet
   ```

## What This Does

This single command will:
1. ✅ Create/update the SQLite database (`mtg_draft_coach.db`)
2. ✅ Process all draft picks from the draft data file
3. ✅ Process all game results from the game data file
4. ✅ Calculate all win rate statistics (opening hand, drawn, overall)
5. ✅ Calculate archetype statistics
6. ✅ Create draft summaries
7. ✅ Store everything in the database, ready for RAG queries

## Optional Flags

**Use a custom database name:**
```bash
python mtg_draft_pipeline.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet --db my_custom_db.db
```

**Skip Scryfall API (faster, but less complete card metadata):**
```bash
python mtg_draft_pipeline.py TLA draft_data_public.TLA.PremierDraft.parquet game_data_public.TLA.PremierDraft.parquet --no-scryfall
```

## Expected Output

You'll see progress bars and messages like:
```
============================================================
MTG Draft Data Pipeline
============================================================
Set: TLA
Draft Data: draft_data_public.TLA.PremierDraft.parquet
Game Data: game_data_public.TLA.PremierDraft.parquet
============================================================
Creating database schema...
✓ Database schema created successfully
Processing draft data from draft_data_public.TLA.PremierDraft.parquet...
  Total rows: 1,234,567
  Found 350 unique cards in draft data
Processing 350 unique cards...
...
✓ Pipeline completed successfully!
  Time elapsed: 0:15:32
  Database: mtg_draft_coach.db
============================================================
```

## Verify It Worked

After completion, check the database exists:
```bash
dir mtg_draft_coach.db
```

Or query it:
```python
import sqlite3
conn = sqlite3.connect('mtg_draft_coach.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM cards WHERE set = 'TLA'")
print(f"Cards in database: {cursor.fetchone()[0]}")
conn.close()
```

