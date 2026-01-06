# How to Query mtg_draft_coach.db

This guide shows you how to query the SQLite database created by the pipeline.

## Method 1: Command Line (sqlite3)

### Basic Usage

```bash
cd POC_work
sqlite3 mtg_draft_coach.db
```

Once in the SQLite prompt, you can run queries:

```sql
-- List all tables
.tables

-- Show schema for a table
.schema cards

-- Run a query
SELECT card_name, overall_wr FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs."set" = 'TLA'
ORDER BY overall_wr DESC
LIMIT 10;

-- Exit
.quit
```

### One-Line Queries

```bash
# Windows PowerShell
sqlite3 POC_work\mtg_draft_coach.db "SELECT COUNT(*) FROM cards WHERE \"set\" = 'TLA';"

# Linux/Mac
sqlite3 POC_work/mtg_draft_coach.db "SELECT COUNT(*) FROM cards WHERE \"set\" = 'TLA';"
```

## Method 2: Python Script

### Basic Connection

```python
import sqlite3

# Connect to database
conn = sqlite3.connect('POC_work/mtg_draft_coach.db')
cursor = conn.cursor()

# Run a query
cursor.execute("""
    SELECT card_name, overall_wr, gih_wr, drawn_wr
    FROM card_statistics cs
    JOIN cards c ON cs.card_id = c.card_id
    WHERE cs."set" = 'TLA'
      AND cs.total_games >= 100
    ORDER BY overall_wr DESC
    LIMIT 10
""")

results = cursor.fetchall()
for row in results:
    print(row)

conn.close()
```

### Using Context Manager (Recommended)

```python
import sqlite3

with sqlite3.connect('POC_work/mtg_draft_coach.db') as conn:
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT card_name, overall_wr
        FROM card_statistics cs
        JOIN cards c ON cs.card_id = c.card_id
        WHERE cs."set" = 'TLA'
        ORDER BY overall_wr DESC
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        print(row)
```

## Example Queries

### 1. Top Cards by Overall Win Rate

```sql
SELECT 
    c.card_name,
    cs.overall_wr,
    cs.gih_wr AS opening_hand_wr,
    cs.drawn_wr,
    cs.total_games
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs."set" = 'TLA'
  AND cs.total_games >= 100
  AND cs.overall_wr IS NOT NULL
ORDER BY cs.overall_wr DESC
LIMIT 20;
```

### 2. Best Color Combinations (Archetypes)

```sql
SELECT 
    main_colors,
    COALESCE(splash_colors, '') AS splash,
    win_rate,
    total_games,
    total_wins,
    total_losses
FROM color_archetypes
WHERE "set" = 'TLA'
  AND total_games >= 50
ORDER BY win_rate DESC
LIMIT 15;
```

### 3. Find a Specific Card's Stats

```sql
SELECT 
    c.card_name,
    c.color_identity,
    c.cmc,
    c.card_type,
    cs.gih_wr AS opening_hand_wr,
    cs.drawn_wr,
    cs.overall_wr,
    cs.total_games,
    cs.avg_pick_number,
    cs.maindeck_rate
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE c.card_name LIKE '%lightning%'
  AND cs."set" = 'TLA';
```

### 4. Cards by Color Identity

```sql
SELECT 
    c.card_name,
    c.color_identity,
    cs.overall_wr,
    cs.total_games
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs."set" = 'TLA'
  AND c.color_identity = 'UR'  -- Blue-Red
  AND cs.total_games >= 50
ORDER BY cs.overall_wr DESC;
```

### 5. Cards by Converted Mana Cost (CMC)

```sql
SELECT 
    c.card_name,
    c.cmc,
    cs.overall_wr,
    cs.total_games,
    cs.avg_pick_number
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs."set" = 'TLA'
  AND c.cmc = 2
  AND cs.total_games >= 50
ORDER BY cs.overall_wr DESC
LIMIT 20;
```

### 6. Compare Opening Hand vs Drawn Win Rate

```sql
SELECT 
    c.card_name,
    cs.gih_wr AS opening_hand_wr,
    cs.drawn_wr,
    cs.overall_wr,
    cs.gih_games,
    cs.drawn_games,
    (cs.gih_wr - cs.drawn_wr) AS difference
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs."set" = 'TLA'
  AND cs.gih_games >= 50
  AND cs.drawn_games >= 50
ORDER BY ABS(cs.gih_wr - cs.drawn_wr) DESC
LIMIT 20;
```

### 7. Draft Performance Summary

```sql
SELECT 
    rank,
    COUNT(*) AS total_drafts,
    AVG(win_rate) AS avg_win_rate,
    AVG(total_games) AS avg_games_per_draft,
    SUM(total_wins) AS total_wins,
    SUM(total_losses) AS total_losses
FROM draft_summaries
WHERE "set" = 'TLA'
GROUP BY rank
ORDER BY rank;
```

### 8. Most Picked Cards (by Average Pick Number)

```sql
SELECT 
    c.card_name,
    cs.avg_pick_number,
    cs.total_picks,
    cs.overall_wr,
    cs.maindeck_rate
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs."set" = 'TLA'
  AND cs.total_picks >= 100
ORDER BY cs.avg_pick_number ASC  -- Lower = picked earlier
LIMIT 20;
```

### 9. Cards with High Maindeck Rate

```sql
SELECT 
    c.card_name,
    cs.maindeck_rate,
    cs.overall_wr,
    cs.total_picks,
    cs.total_games
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs."set" = 'TLA'
  AND cs.total_picks >= 50
  AND cs.maindeck_rate >= 0.8  -- 80%+ maindeck rate
ORDER BY cs.maindeck_rate DESC, cs.overall_wr DESC;
```

### 10. Archetype Matchup Analysis

```sql
SELECT 
    main_colors,
    opp_colors,
    COUNT(*) AS games,
    SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) AS wins,
    ROUND(100.0 * SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate
FROM game_results
WHERE "set" = 'TLA'
  AND main_colors IS NOT NULL
  AND opp_colors IS NOT NULL
GROUP BY main_colors, opp_colors
HAVING games >= 20
ORDER BY win_rate DESC;
```

## Python Helper Script

Create a file `query_db.py`:

```python
import sqlite3
import sys

def query_database(query, db_path='POC_work/mtg_draft_coach.db'):
    """Execute a query and return results."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

def print_results(results, headers=None):
    """Pretty print query results."""
    if not results:
        print("No results found.")
        return
    
    if headers:
        print(" | ".join(headers))
        print("-" * (len(" | ".join(headers))))
    
    for row in results:
        print(" | ".join(str(x) if x is not None else "N/A" for x in row))

# Example usage
if __name__ == "__main__":
    # Top 10 cards by overall win rate
    query = """
        SELECT 
            c.card_name,
            cs.overall_wr,
            cs.total_games
        FROM card_statistics cs
        JOIN cards c ON cs.card_id = c.card_id
        WHERE cs."set" = 'TLA'
          AND cs.total_games >= 100
        ORDER BY cs.overall_wr DESC
        LIMIT 10
    """
    
    results = query_database(query)
    print_results(results, ["Card Name", "Overall WR", "Total Games"])
```

Run it:
```bash
cd POC_work
python query_db.py
```

## Important Notes

1. **Escaping `set` column**: The `set` column is a reserved keyword in SQLite, so always use `"set"` (double quotes) when referencing it.

2. **Table Names**:
   - `cards` - Card master data
   - `card_statistics` - Card performance metrics
   - `color_archetypes` - Color combination statistics
   - `draft_picks` - Individual draft picks
   - `draft_summaries` - Draft-level summaries
   - `game_results` - Game-level results
   - `game_cards` - Card usage in games

3. **Win Rate Values**: All win rates are stored as decimals (0.0-1.0). Multiply by 100 to get percentages.

4. **Filtering by Sample Size**: Always filter by `total_games >= N` or `total_picks >= N` to avoid misleading statistics from small sample sizes.

## Quick Reference: Table Relationships

```
cards (1) ──< (many) card_statistics
cards (1) ──< (many) draft_picks
cards (1) ──< (many) game_cards
draft_summaries (1) ──< (many) draft_picks
draft_summaries (1) ──< (many) game_results
game_results (1) ──< (many) game_cards
```

