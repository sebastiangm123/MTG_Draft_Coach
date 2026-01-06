# Database Schema Plan for MTG Draft Coach

## Data Analysis Summary

### Draft Data (`draft_data_public.TLA.PremierDraft.csv`)
- **709 columns** - One row per draft pick
- Key fields: `expansion`, `event_type`, `draft_id`, `draft_time`, `rank`, `event_match_wins`, `event_match_losses`, `pack_number`, `pick_number`, `pick` (card name)
- Binary indicators: `pack_card_X` (card in pack), `pool_X` (card in pool)
- Rates: `pick_maindeck_rate`, `pick_sideboard_in_rate`

### Game Data (`game_data_public.TLA.PremierDraft.csv`)
- **1755 columns** - One row per game
- Key fields: `expansion`, `event_type`, `draft_id`, `game_time`, `rank`, `opp_rank`, `main_colors`, `splash_colors`, `opp_colors`, `won`, `num_turns`, `on_play`
- Per-card tracking: `opening_hand_X`, `drawn_X`, `tutored_X`, `deck_X`, `sideboard_X` for each card

---

## Proposed Database Schema

### Table 1: `cards` - Card Master Data
**Purpose**: Normalized card information for easy lookup and RAG embedding

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `card_id` | INTEGER PRIMARY KEY | Auto-increment ID | PK |
| `card_name` | TEXT NOT NULL | Normalized card name (lowercase) | UNIQUE |
| `set` | TEXT NOT NULL | Set code (e.g., "TLA") | INDEX |
| `color_identity` | TEXT | WUBRG order (e.g., "UBG") | INDEX |
| `card_type` | TEXT | Full type line | |
| `cmc` | INTEGER | Converted mana cost | INDEX |
| `rarity` | TEXT | Common, Uncommon, Rare, Mythic | |
| `created_at` | TIMESTAMP | Record creation time | |

**Use Cases**:
- Fast card lookups by name
- Filter by color identity for archetype queries
- Filter by CMC for curve analysis
- RAG: Embed card metadata for semantic search

---

### Table 2: `card_statistics` - Card Performance Metrics
**Purpose**: Aggregated card statistics including GIH WR

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `card_stat_id` | INTEGER PRIMARY KEY | Auto-increment ID | PK |
| `card_id` | INTEGER | FK to cards | FK, INDEX |
| `set` | TEXT NOT NULL | Set code | INDEX |
| `event_type` | TEXT | PremierDraft, QuickDraft, etc. | INDEX |
| `gih_wr` | REAL | Opening Hand Win Rate (0.0-1.0) - Win rate when card was in opening hand | INDEX |
| `gih_games` | INTEGER | Total games where card was in opening hand | |
| `gih_wins` | INTEGER | Wins when card was in opening hand | |
| `drawn_wr` | REAL | Drawn Win Rate (0.0-1.0) - Win rate when card was drawn during game | INDEX |
| `drawn_games` | INTEGER | Total games where card was drawn | |
| `drawn_wins` | INTEGER | Wins when card was drawn | |
| `overall_wr` | REAL | Overall Win Rate (0.0-1.0) - Average of opening hand and drawn win rates | INDEX |
| `ever_drawn_wr` | REAL | Win rate when card was ever drawn | |
| `maindeck_wr` | REAL | Win rate when card was in maindeck | |
| `avg_pick_number` | REAL | Average pick position (1-45) | |
| `avg_pack_number` | REAL | Average pack number when picked | |
| `total_picks` | INTEGER | Total times card was picked | |
| `total_games` | INTEGER | Total games played with card | |
| `total_wins` | INTEGER | Total wins with card | |
| `total_losses` | INTEGER | Total losses with card | |
| `maindeck_rate` | REAL | % of time card made maindeck | |
| `sideboard_rate` | REAL | % of time card was sideboarded | |
| `last_updated` | TIMESTAMP | Last statistics update | |

**Use Cases**:
- Query opening hand win rate (GIH WR) for specific cards
- Query drawn win rate for cards that were drawn during games
- Query overall win rate (average of opening hand and drawn win rates)
- Compare card performance across formats
- RAG: Include performance metrics in card context

**Win Rate Metrics**:
- **Opening Hand Win Rate (GIH WR)**: `gih_wins / gih_games` - Win rate when card was in the opening hand
- **Drawn Win Rate**: `drawn_wins / drawn_games` - Win rate when card was drawn during the game (but not necessarily in opening hand)
- **Overall Win Rate**: `(gih_wr + drawn_wr) / 2` - Average of opening hand win rate and drawn win rate

---

### Table 3: `color_archetypes` - Color Combination Statistics
**Purpose**: Win rates and statistics for color combinations (archetype-level metrics)

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `archetype_id` | INTEGER PRIMARY KEY | Auto-increment ID | PK |
| `set` | TEXT NOT NULL | Set code | INDEX |
| `event_type` | TEXT | Draft format | INDEX |
| `main_colors` | TEXT NOT NULL | Primary colors (WUBRG order, e.g., "UB") | INDEX |
| `splash_colors` | TEXT | Splash colors (WUBRG order, e.g., "R") | |
| `full_color_identity` | TEXT | Combined (e.g., "UBR") | INDEX |
| `total_games` | INTEGER | Total games played | |
| `total_wins` | INTEGER | Total wins | |
| `total_losses` | INTEGER | Total losses | |
| `win_rate` | REAL | Archetype Overall Win Rate (0.0-1.0) - Total wins / total games for this color combination | INDEX |
| `avg_num_turns` | REAL | Average game length | |
| `on_play_win_rate` | REAL | Archetype Win Rate when on play | |
| `on_draw_win_rate` | REAL | Archetype Win Rate when on draw | |
| `avg_mulligans` | REAL | Average mulligans per game | |
| `last_updated` | TIMESTAMP | Last statistics update | |

**Use Cases**:
- Query archetype win rates for specific color combinations
- Compare archetype performance
- RAG: Include archetype context in recommendations

---

### Table 4: `draft_picks` - Individual Pick Records
**Purpose**: Track each pick in every draft for analysis

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `pick_id` | INTEGER PRIMARY KEY | Auto-increment ID | PK |
| `draft_id` | TEXT NOT NULL | Unique draft identifier | INDEX |
| `set` | TEXT NOT NULL | Set code | INDEX |
| `event_type` | TEXT | Draft format | INDEX |
| `draft_time` | TIMESTAMP | When draft occurred | INDEX |
| `rank` | TEXT | Player rank (bronze, silver, etc.) | INDEX |
| `pack_number` | INTEGER | Pack number (0-2) | |
| `pick_number` | INTEGER | Pick number within pack (0-14) | |
| `card_id` | INTEGER | FK to cards | FK, INDEX |
| `card_name` | TEXT | Card name (denormalized for queries) | INDEX |
| `pick_2` | TEXT | Second choice card (if available) | |
| `maindeck_rate` | REAL | Did this pick make maindeck? | |
| `sideboard_rate` | REAL | Was this pick sideboarded? | |
| `event_match_wins` | INTEGER | Wins in this draft event | |
| `event_match_losses` | INTEGER | Losses in this draft event | |
| `created_at` | TIMESTAMP | Record creation time | |

**Use Cases**:
- Analyze pick patterns
- Track draft performance
- RAG: Context about when/where cards are typically picked

---

### Table 5: `draft_summaries` - Draft-Level Aggregations
**Purpose**: Summary statistics per draft

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `draft_summary_id` | INTEGER PRIMARY KEY | Auto-increment ID | PK |
| `draft_id` | TEXT NOT NULL UNIQUE | Unique draft identifier | UNIQUE, INDEX |
| `set` | TEXT NOT NULL | Set code | INDEX |
| `event_type` | TEXT | Draft format | INDEX |
| `draft_time` | TIMESTAMP | When draft occurred | INDEX |
| `rank` | TEXT | Player rank | INDEX |
| `final_colors` | TEXT | Final deck colors (WUBRG order) | INDEX |
| `splash_colors` | TEXT | Splash colors | |
| `total_games` | INTEGER | Total games played | |
| `total_wins` | INTEGER | Total wins | |
| `total_losses` | INTEGER | Total losses | |
| `win_rate` | REAL | Draft Overall Win Rate (0.0-1.0) - Total wins / total games for this draft | INDEX |
| `avg_game_length` | REAL | Average turns per game | |
| `total_picks` | INTEGER | Total picks in draft (should be 45) | |
| `created_at` | TIMESTAMP | Record creation time | |

**Use Cases**:
- Quick draft performance lookups
- Analyze draft outcomes
- RAG: Context about successful draft patterns

---

### Table 6: `game_results` - Individual Game Records
**Purpose**: Detailed game-level data for win rate calculations

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `game_id` | INTEGER PRIMARY KEY | Auto-increment ID | PK |
| `draft_id` | TEXT NOT NULL | FK to draft | INDEX |
| `set` | TEXT NOT NULL | Set code | INDEX |
| `event_type` | TEXT | Draft format | INDEX |
| `game_time` | TIMESTAMP | When game occurred | INDEX |
| `match_number` | INTEGER | Match number in event | |
| `game_number` | INTEGER | Game number in match | |
| `rank` | TEXT | Player rank | INDEX |
| `opp_rank` | TEXT | Opponent rank | |
| `main_colors` | TEXT | Player's main colors | INDEX |
| `splash_colors` | TEXT | Player's splash colors | |
| `opp_colors` | TEXT | Opponent's colors | |
| `on_play` | BOOLEAN | Was player on play? | |
| `num_mulligans` | INTEGER | Player mulligans | |
| `opp_num_mulligans` | INTEGER | Opponent mulligans | |
| `num_turns` | INTEGER | Game length in turns | |
| `won` | BOOLEAN | Did player win? | INDEX |
| `created_at` | TIMESTAMP | Record creation time | |

**Use Cases**:
- Calculate card win rates (join with game_cards)
- Analyze game outcomes
- RAG: Context about game patterns

---

### Table 7: `game_cards` - Card Presence in Games
**Purpose**: Track which cards were in hand/deck for each game (for win rate calculations)

| Column | Type | Description | Index |
|--------|------|-------------|-------|
| `game_card_id` | INTEGER PRIMARY KEY | Auto-increment ID | PK |
| `game_id` | INTEGER NOT NULL | FK to game_results | FK, INDEX |
| `card_id` | INTEGER NOT NULL | FK to cards | FK, INDEX |
| `in_opening_hand` | BOOLEAN | Was card in opening hand? | INDEX |
| `was_drawn` | BOOLEAN | Was card drawn during game? | |
| `was_tutored` | BOOLEAN | Was card tutored? | |
| `in_maindeck` | BOOLEAN | Was card in maindeck? | |
| `in_sideboard` | BOOLEAN | Was card in sideboard? | |
| `created_at` | TIMESTAMP | Record creation time | |

**Use Cases**:
- Calculate Opening Hand Win Rate: `SUM(won WHERE in_opening_hand=1) / COUNT(*) WHERE in_opening_hand=1`
- Calculate Drawn Win Rate: `SUM(won WHERE was_drawn=1) / COUNT(*) WHERE was_drawn=1`
- Track card usage patterns
- RAG: Context about card performance in games

**Note**: This is a junction table - one row per card per game

---

## Schema Relationships

```
cards (1) ──< (many) card_statistics
cards (1) ──< (many) draft_picks
cards (1) ──< (many) game_cards
draft_summaries (1) ──< (many) draft_picks
draft_summaries (1) ──< (many) game_results
game_results (1) ──< (many) game_cards
```

---

## Key Queries for RAG Component

### 1. Get Card Win Rates (Opening Hand, Drawn & Overall)
```sql
SELECT card_name, gih_wr, gih_games, gih_wins, drawn_wr, drawn_games, drawn_wins, overall_wr
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE c.card_name = ? AND cs.set = ?
```

### 2. Get Color Combination (Archetype) Win Rate
```sql
SELECT main_colors, splash_colors, win_rate AS archetype_win_rate, total_games
FROM color_archetypes
WHERE set = ? AND main_colors = ?
ORDER BY win_rate DESC
```

### 3. Get Card Performance in Specific Archetype
```sql
SELECT c.card_name, cs.gih_wr, cs.drawn_wr, cs.overall_wr
FROM card_statistics cs
JOIN cards c ON cs.card_id = c.card_id
WHERE cs.set = ? 
  AND EXISTS (
    SELECT 1 FROM draft_summaries ds
    WHERE ds.draft_id IN (
      SELECT draft_id FROM draft_picks WHERE card_id = c.card_id
    ) AND ds.final_colors LIKE ?
  )
```

### 4. Get Similar Cards (by color/CMC)
```sql
SELECT card_name, gih_wr, drawn_wr, overall_wr, color_identity, cmc
FROM cards c
JOIN card_statistics cs ON c.card_id = cs.card_id
WHERE cs.set = ?
  AND color_identity = ?
  AND cmc BETWEEN ? AND ?
ORDER BY overall_wr DESC
```

---

## Data Processing Pipeline Considerations

### Step 1: Normalize Card Data
- Extract unique cards from draft_data
- Fetch metadata from Scryfall (color_identity, cmc, card_type)
- Populate `cards` table

### Step 2: Process Draft Picks
- Extract picks from draft_data
- Link to cards table
- Populate `draft_picks` table
- Aggregate to `draft_summaries`

### Step 3: Process Game Data
- Extract game results from game_data
- Populate `game_results` table
- Extract card presence data (opening_hand_X, drawn_X, etc.)
- Populate `game_cards` junction table

### Step 4: Calculate Statistics
- Calculate Opening Hand Win Rate (GIH WR): Aggregate from `game_cards` (where `in_opening_hand=1`) + `game_results`
  - Formula: `gih_wr = gih_wins / gih_games`
- Calculate Drawn Win Rate: Aggregate from `game_cards` (where `was_drawn=1`) + `game_results`
  - Formula: `drawn_wr = drawn_wins / drawn_games`
- Calculate Overall Win Rate: Average of opening hand and drawn win rates
  - Formula: `overall_wr = (gih_wr + drawn_wr) / 2`
- Calculate color archetype win rates: Aggregate from `game_results`
  - Formula: `win_rate = total_wins / total_games` (for each color combination)
- Populate `card_statistics` and `color_archetypes` tables

---

## RAG Optimization Notes

1. **Pre-compute common queries**: Store frequently accessed metrics
2. **Denormalize for speed**: Include card_name in statistics tables for faster lookups
3. **Index strategically**: Index on set, color_identity, gih_wr, drawn_wr, overall_wr for fast filtering
4. **Embedding-friendly**: Structure allows easy extraction of card + stats for embeddings
5. **Context-rich**: Multiple tables provide different context levels (card, archetype, draft, game)

---

## Alternative: Denormalized View for RAG

Consider creating a materialized view or denormalized table:

### `card_context` (Denormalized for RAG)
- Combines: cards + card_statistics + color_archetypes (where applicable)
- Single query gets all context needed for embedding
- Update periodically from normalized tables

This would make RAG queries much faster but requires maintaining consistency.

