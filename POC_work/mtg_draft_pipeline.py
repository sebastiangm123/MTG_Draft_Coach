"""
MTG Draft Data Pipeline
Processes Parquet files and creates RAG-optimized SQLite database for any Magic: The Gathering set.

This pipeline:
1. Reads draft_data and game_data Parquet files
2. Dynamically extracts card names from column names
3. Processes all draft picks and game results
4. Calculates win rate metrics (opening hand, drawn, overall)
5. Creates normalized SQLite database optimized for RAG queries
"""

import sqlite3
import pandas as pd
import pyarrow.parquet as pq
import re
import os
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import requests
import time
from tqdm import tqdm


class MTGDraftPipeline:
    """Main pipeline class for processing MTG draft data."""
    
    # Column prefixes that indicate card names
    CARD_COLUMN_PREFIXES = {
        'pack_card_': 'pack',
        'pool_': 'pool',
        'opening_hand_': 'opening_hand',
        'drawn_': 'drawn',
        'tutored_': 'tutored',
        'deck_': 'deck',
        'sideboard_': 'sideboard'
    }
    
    def __init__(self, db_path: str = "mtg_draft_coach.db", use_scryfall: bool = True):
        """Initialize pipeline with database path."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.card_cache = {}  # Cache for Scryfall API calls
        self.api_delay = 0.1  # Rate limiting for Scryfall API
        self.use_scryfall = use_scryfall  # Whether to use Scryfall API
        
    def connect_db(self):
        """Connect to SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")  # Better performance
        self.cursor = self.conn.cursor()
        
    def close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            
    def create_schema(self):
        """Create all database tables according to schema plan."""
        print("Creating database schema...")
        
        # Table 1: cards
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                "set" TEXT NOT NULL,
                color_identity TEXT,
                card_type TEXT,
                cmc INTEGER,
                rarity TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(card_name, "set")
            )
        """)
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_name ON cards(card_name)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_set ON cards("set")')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_color ON cards(color_identity)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_cards_cmc ON cards(cmc)')
        
        # Table 2: card_statistics
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_statistics (
                card_stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                "set" TEXT NOT NULL,
                event_type TEXT,
                gih_wr REAL,
                gih_games INTEGER DEFAULT 0,
                gih_wins INTEGER DEFAULT 0,
                drawn_wr REAL,
                drawn_games INTEGER DEFAULT 0,
                drawn_wins INTEGER DEFAULT 0,
                overall_wr REAL,
                ever_drawn_wr REAL,
                maindeck_wr REAL,
                avg_pick_number REAL,
                avg_pack_number REAL,
                total_picks INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                maindeck_rate REAL,
                sideboard_rate REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (card_id) REFERENCES cards(card_id),
                UNIQUE(card_id, "set", event_type)
            )
        """)
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_stats_card ON card_statistics(card_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_stats_set ON card_statistics("set")')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_stats_event_type ON card_statistics(event_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_stats_gih_wr ON card_statistics(gih_wr)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_stats_drawn_wr ON card_statistics(drawn_wr)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_stats_overall_wr ON card_statistics(overall_wr)')
        
        # Table 3: color_archetypes
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS color_archetypes (
                archetype_id INTEGER PRIMARY KEY AUTOINCREMENT,
                "set" TEXT NOT NULL,
                event_type TEXT,
                main_colors TEXT NOT NULL,
                splash_colors TEXT,
                full_color_identity TEXT,
                total_games INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                win_rate REAL,
                avg_num_turns REAL,
                on_play_win_rate REAL,
                on_draw_win_rate REAL,
                avg_mulligans REAL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE("set", event_type, main_colors, splash_colors)
            )
        """)
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_archetypes_set ON color_archetypes("set")')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_archetypes_event_type ON color_archetypes(event_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_archetypes_colors ON color_archetypes(main_colors)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_archetypes_full_colors ON color_archetypes(full_color_identity)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_archetypes_win_rate ON color_archetypes(win_rate)')
        
        # Table 4: draft_picks
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS draft_picks (
                pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id TEXT NOT NULL,
                "set" TEXT NOT NULL,
                event_type TEXT,
                draft_time TIMESTAMP,
                rank TEXT,
                pack_number INTEGER,
                pick_number INTEGER,
                card_id INTEGER,
                card_name TEXT,
                pick_2 TEXT,
                maindeck_rate REAL,
                sideboard_rate REAL,
                event_match_wins INTEGER,
                event_match_losses INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (card_id) REFERENCES cards(card_id)
            )
        """)
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_picks_draft ON draft_picks(draft_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_picks_card ON draft_picks(card_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_picks_set ON draft_picks("set")')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_picks_event_type ON draft_picks(event_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_picks_draft_time ON draft_picks(draft_time)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_picks_rank ON draft_picks(rank)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_picks_card_name ON draft_picks(card_name)')
        
        # Table 5: draft_summaries
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS draft_summaries (
                draft_summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id TEXT NOT NULL UNIQUE,
                "set" TEXT NOT NULL,
                event_type TEXT,
                draft_time TIMESTAMP,
                rank TEXT,
                final_colors TEXT,
                splash_colors TEXT,
                total_games INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                win_rate REAL,
                avg_game_length REAL,
                total_picks INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_summaries_set ON draft_summaries("set")')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_summaries_colors ON draft_summaries(final_colors)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_summaries_event_type ON draft_summaries(event_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_summaries_draft_time ON draft_summaries(draft_time)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_summaries_rank ON draft_summaries(rank)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_draft_summaries_win_rate ON draft_summaries(win_rate)')
        
        # Table 6: game_results
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_results (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id TEXT NOT NULL,
                "set" TEXT NOT NULL,
                event_type TEXT,
                game_time TIMESTAMP,
                match_number INTEGER,
                game_number INTEGER,
                rank TEXT,
                opp_rank TEXT,
                main_colors TEXT,
                splash_colors TEXT,
                opp_colors TEXT,
                on_play BOOLEAN,
                num_mulligans INTEGER,
                opp_num_mulligans INTEGER,
                num_turns INTEGER,
                won BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_results_draft ON game_results(draft_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_results_won ON game_results(won)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_results_set ON game_results("set")')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_results_event_type ON game_results(event_type)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_results_game_time ON game_results(game_time)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_results_rank ON game_results(rank)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_results_main_colors ON game_results(main_colors)')
        
        # Table 7: game_cards
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_cards (
                game_card_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                in_opening_hand BOOLEAN DEFAULT 0,
                was_drawn BOOLEAN DEFAULT 0,
                was_tutored BOOLEAN DEFAULT 0,
                in_maindeck BOOLEAN DEFAULT 0,
                in_sideboard BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES game_results(game_id),
                FOREIGN KEY (card_id) REFERENCES cards(card_id),
                UNIQUE(game_id, card_id)
            )
        """)
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_cards_game ON game_cards(game_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_cards_card ON game_cards(card_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_cards_opening_hand ON game_cards(in_opening_hand)")
        
        self.conn.commit()
        print("[OK] Database schema created successfully")
        
    def extract_card_names(self, df: pd.DataFrame) -> Set[str]:
        """Extract unique card names from column names dynamically."""
        card_names = set()
        
        for col in df.columns:
            for prefix, _ in self.CARD_COLUMN_PREFIXES.items():
                if col.startswith(prefix):
                    # Extract card name after prefix
                    card_name = col[len(prefix):]
                    if card_name:  # Ensure not empty
                        card_names.add(card_name)
        
        return card_names
    
    def normalize_card_name(self, card_name: str) -> str:
        """Normalize card name to lowercase for consistency."""
        return card_name.lower().strip()
    
    def parse_mana_cost(self, mana_cost: str) -> Tuple[Optional[int], str]:
        """
        Parse mana cost to extract CMC and color identity.
        Returns: (cmc, color_identity)
        """
        if not mana_cost or mana_cost == "None" or pd.isna(mana_cost):
            return None, ""
        
        cmc = 0
        colors = set()
        mana_symbols = re.findall(r'\{([^{}]+)\}', str(mana_cost))
        
        for symbol in mana_symbols:
            symbol_upper = symbol.upper()
            if symbol_upper in ['W', 'U', 'B', 'R', 'G']:
                colors.add(symbol_upper)
                cmc += 1
            elif symbol_upper == 'C':
                cmc += 1
            elif symbol_upper.isdigit():
                cmc += int(symbol_upper)
            elif '/' in symbol_upper:  # Hybrid mana
                cmc += 1
                for p in symbol_upper.split('/'):
                    if p in ['W', 'U', 'B', 'R', 'G']:
                        colors.add(p)
            elif symbol_upper.endswith('/P'):  # Phyrexian mana
                cmc += 1
                if symbol_upper[0] in ['W', 'U', 'B', 'R', 'G']:
                    colors.add(symbol_upper[0])
            elif symbol_upper in ['X', 'Y', 'Z']:
                cmc = None  # Variable CMC
                break
        
        color_order = ['W', 'U', 'B', 'R', 'G']
        color_identity = "".join(sorted(list(colors), key=lambda c: color_order.index(c) if c in color_order else 999))
        
        return cmc, color_identity
    
    def get_card_from_scryfall(self, card_name: str, set_code: str) -> Optional[Dict]:
        """Fetch card metadata from Scryfall API with caching."""
        cache_key = f"{card_name}_{set_code}"
        if cache_key in self.card_cache:
            return self.card_cache[cache_key]
        
        try:
            # Scryfall API search
            url = f"https://api.scryfall.com/cards/search"
            params = {
                'q': f'!"{card_name}" set:{set_code.lower()}',
                'unique': 'prints'
            }
            
            time.sleep(self.api_delay)  # Rate limiting
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    card = data['data'][0]
                    result = {
                        'name': card.get('name', card_name),
                        'mana_cost': card.get('mana_cost', ''),
                        'type_line': card.get('type_line', ''),
                        'cmc': card.get('cmc', None),
                        'rarity': card.get('rarity', ''),
                        'color_identity': ''.join(card.get('color_identity', []))
                    }
                    self.card_cache[cache_key] = result
                    return result
        except Exception as e:
            print(f"  Warning: Could not fetch {card_name} from Scryfall: {e}")
        
        return None
    
    def process_cards(self, card_names: Set[str], set_code: str, use_scryfall: bool = True):
        """Process and insert cards into database."""
        print(f"\nProcessing {len(card_names)} unique cards...")
        
        cards_inserted = 0
        cards_skipped = 0
        
        for card_name in tqdm(card_names, desc="Processing cards"):
            normalized_name = self.normalize_card_name(card_name)
            
            # Check if card already exists
            self.cursor.execute(
                'SELECT card_id FROM cards WHERE card_name = ? AND "set" = ?',
                (normalized_name, set_code)
            )
            existing = self.cursor.fetchone()
            
            if existing:
                cards_skipped += 1
                continue
            
            # Try to get metadata from Scryfall
            color_identity = ""
            card_type = ""
            cmc = None
            rarity = None
            
            if use_scryfall:
                scryfall_data = self.get_card_from_scryfall(card_name, set_code)
                if scryfall_data:
                    color_identity = scryfall_data.get('color_identity', '')
                    card_type = scryfall_data.get('type_line', '')
                    cmc = scryfall_data.get('cmc')
                    rarity = scryfall_data.get('rarity', '')
                    
                    # If no color_identity from API, try parsing mana_cost
                    if not color_identity and scryfall_data.get('mana_cost'):
                        _, color_identity = self.parse_mana_cost(scryfall_data['mana_cost'])
                else:
                    # Fallback: try to parse if we have any info
                    pass
            
            # Insert card
            self.cursor.execute("""
                INSERT INTO cards (card_name, "set", color_identity, card_type, cmc, rarity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (normalized_name, set_code, color_identity, card_type, cmc, rarity))
            cards_inserted += 1
            
            if cards_inserted % 100 == 0:
                self.conn.commit()
        
        self.conn.commit()
        print(f"[OK] Inserted {cards_inserted} cards, skipped {cards_skipped} existing")
        
    def process_draft_data(self, parquet_file: str, set_code: str):
        """Process draft data Parquet file."""
        print(f"\nProcessing draft data from {parquet_file}...")
        
        if not os.path.exists(parquet_file):
            raise FileNotFoundError(f"Draft data file not found: {parquet_file}")
        
        # Read Parquet file in chunks
        parquet_file_obj = pq.ParquetFile(parquet_file)
        total_rows = parquet_file_obj.metadata.num_rows
        print(f"  Total rows: {total_rows:,}")
        
        # Read first batch to get schema and extract card names
        first_batch = next(parquet_file_obj.iter_batches(batch_size=1000))
        first_df = first_batch.to_pandas()
        
        # Extract card names from columns
        card_names = self.extract_card_names(first_df)
        print(f"  Found {len(card_names)} unique cards in draft data")
        
        # Process cards first
        self.process_cards(card_names, set_code, use_scryfall=self.use_scryfall)
        
        # Get card_id mapping
        self.cursor.execute('SELECT card_id, card_name FROM cards WHERE "set" = ?', (set_code,))
        card_id_map = {name: cid for cid, name in self.cursor.fetchall()}
        
        # Process draft picks
        picks_inserted = 0
        batch_size = 10000
        
        print("Processing draft picks...")
        for batch in tqdm(parquet_file_obj.iter_batches(batch_size=batch_size), 
                         total=(total_rows // batch_size) + 1,
                         desc="Processing picks"):
            df = batch.to_pandas()
            
            for _, row in df.iterrows():
                pick_card_name = row.get('pick', '')
                if not pick_card_name or pd.isna(pick_card_name):
                    continue
                
                normalized_name = self.normalize_card_name(pick_card_name)
                card_id = card_id_map.get(normalized_name)
                
                # Insert draft pick
                self.cursor.execute("""
                    INSERT INTO draft_picks (
                        draft_id, "set", event_type, draft_time, rank,
                        pack_number, pick_number, card_id, card_name,
                        pick_2, maindeck_rate, sideboard_rate,
                        event_match_wins, event_match_losses
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get('draft_id', ''),
                    set_code,
                    row.get('event_type', ''),
                    row.get('draft_time', None),
                    row.get('rank', ''),
                    row.get('pack_number', None),
                    row.get('pick_number', None),
                    card_id,
                    normalized_name,
                    row.get('pick_2', ''),
                    row.get('pick_maindeck_rate', None),
                    row.get('pick_sideboard_in_rate', None),
                    row.get('event_match_wins', None),
                    row.get('event_match_losses', None)
                ))
                picks_inserted += 1
                
                if picks_inserted % 1000 == 0:
                    self.conn.commit()
        
        self.conn.commit()
        print(f"[OK] Inserted {picks_inserted:,} draft picks")
        
    def process_game_data(self, parquet_file: str, set_code: str):
        """Process game data Parquet file."""
        print(f"\nProcessing game data from {parquet_file}...")
        
        if not os.path.exists(parquet_file):
            raise FileNotFoundError(f"Game data file not found: {parquet_file}")
        
        parquet_file_obj = pq.ParquetFile(parquet_file)
        total_rows = parquet_file_obj.metadata.num_rows
        print(f"  Total rows: {total_rows:,}")
        
        # Read first batch to extract card names
        first_batch = next(parquet_file_obj.iter_batches(batch_size=1000))
        first_df = first_batch.to_pandas()
        
        card_names = self.extract_card_names(first_df)
        print(f"  Found {len(card_names)} unique cards in game data")
        
        # Ensure all cards exist in database (skip Scryfall for game data cards as they should already exist)
        self.process_cards(card_names, set_code, use_scryfall=False)
        
        # Get card_id mapping
        self.cursor.execute('SELECT card_id, card_name FROM cards WHERE "set" = ?', (set_code,))
        card_id_map = {name: cid for cid, name in self.cursor.fetchall()}
        
        # Process games and game_cards
        games_inserted = 0
        game_cards_inserted = 0
        batch_size = 5000
        
        print("Processing games and card presence...")
        for batch in tqdm(parquet_file_obj.iter_batches(batch_size=batch_size),
                         total=(total_rows // batch_size) + 1,
                         desc="Processing games"):
            df = batch.to_pandas()
            
            for _, row in df.iterrows():
                # Insert game result
                self.cursor.execute("""
                    INSERT INTO game_results (
                        draft_id, "set", event_type, game_time,
                        match_number, game_number, rank, opp_rank,
                        main_colors, splash_colors, opp_colors,
                        on_play, num_mulligans, opp_num_mulligans,
                        num_turns, won
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row.get('draft_id', ''),
                    set_code,
                    row.get('event_type', ''),
                    row.get('game_time', None),
                    row.get('match_number', None),
                    row.get('game_number', None),
                    row.get('rank', ''),
                    row.get('opp_rank', ''),
                    row.get('main_colors', ''),
                    row.get('splash_colors', ''),
                    row.get('opp_colors', ''),
                    bool(row.get('on_play', False)),
                    row.get('num_mulligans', None),
                    row.get('opp_num_mulligans', None),
                    row.get('num_turns', None),
                    bool(row.get('won', False))
                ))
                game_id = self.cursor.lastrowid
                games_inserted += 1
                
                # Process card presence for this game
                # Collect all card flags first, then insert once per card
                card_flags = {}  # card_id -> {in_opening_hand, was_drawn, etc.}
                
                # Iterate over row columns (not df.columns to avoid issues)
                for col in row.index:
                    for prefix, field_name in self.CARD_COLUMN_PREFIXES.items():
                        if col.startswith(prefix):
                            card_name = col[len(prefix):]
                            if not card_name:
                                continue
                            
                            normalized_name = self.normalize_card_name(card_name)
                            card_id = card_id_map.get(normalized_name)
                            
                            if card_id:
                                value = row.get(col, 0)
                                if value and pd.notna(value):
                                    try:
                                        # Handle both int and float values
                                        num_value = int(float(value)) if value else 0
                                        if num_value > 0:
                                            # Initialize card flags if not exists
                                            if card_id not in card_flags:
                                                card_flags[card_id] = {
                                                    'in_opening_hand': False,
                                                    'was_drawn': False,
                                                    'was_tutored': False,
                                                    'in_maindeck': False,
                                                    'in_sideboard': False
                                                }
                                            
                                            # Set the appropriate flag
                                            if field_name == 'opening_hand':
                                                card_flags[card_id]['in_opening_hand'] = True
                                            elif field_name == 'drawn':
                                                card_flags[card_id]['was_drawn'] = True
                                            elif field_name == 'tutored':
                                                card_flags[card_id]['was_tutored'] = True
                                            elif field_name == 'deck':
                                                card_flags[card_id]['in_maindeck'] = True
                                            elif field_name == 'sideboard':
                                                card_flags[card_id]['in_sideboard'] = True
                                    except (ValueError, TypeError):
                                        pass  # Skip non-numeric values
                
                # Insert all card flags for this game
                for card_id, flags in card_flags.items():
                    self.cursor.execute("""
                        INSERT OR REPLACE INTO game_cards (
                            game_id, card_id, in_opening_hand, was_drawn,
                            was_tutored, in_maindeck, in_sideboard
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (game_id, card_id, 
                         flags['in_opening_hand'],
                         flags['was_drawn'],
                         flags['was_tutored'],
                         flags['in_maindeck'],
                         flags['in_sideboard']))
                    game_cards_inserted += 1
                
                if games_inserted % 1000 == 0:
                    self.conn.commit()
        
        self.conn.commit()
        print(f"[OK] Inserted {games_inserted:,} games and {game_cards_inserted:,} game_card records")
        
    def calculate_card_statistics(self, set_code: str):
        """Calculate all card statistics from game and draft data."""
        print(f"\nCalculating card statistics for {set_code}...")
        
        # Delete existing statistics for this set
        self.cursor.execute('DELETE FROM card_statistics WHERE "set" = ?', (set_code,))
        
        # Get all cards for this set
        self.cursor.execute('SELECT card_id FROM cards WHERE "set" = ?', (set_code,))
        card_ids = [row[0] for row in self.cursor.fetchall()]
        
        print(f"  Calculating statistics for {len(card_ids)} cards...")
        
        for card_id in tqdm(card_ids, desc="Calculating stats"):
            # Get card info
            self.cursor.execute("SELECT card_name FROM cards WHERE card_id = ?", (card_id,))
            card_name = self.cursor.fetchone()[0]
            
            # Calculate opening hand win rate
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as gih_games,
                    SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) as gih_wins
                FROM game_cards gc
                JOIN game_results gr ON gc.game_id = gr.game_id
                WHERE gc.card_id = ? 
                  AND gc.in_opening_hand = 1
                  AND gr."set" = ?
            """, (card_id, set_code))
            gih_result = self.cursor.fetchone()
            gih_games = gih_result[0] or 0
            gih_wins = gih_result[1] or 0
            gih_wr = (gih_wins / gih_games) if gih_games > 0 else None
            
            # Calculate drawn win rate
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as drawn_games,
                    SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) as drawn_wins
                FROM game_cards gc
                JOIN game_results gr ON gc.game_id = gr.game_id
                WHERE gc.card_id = ? 
                  AND gc.was_drawn = 1
                  AND gr."set" = ?
            """, (card_id, set_code))
            drawn_result = self.cursor.fetchone()
            drawn_games = drawn_result[0] or 0
            drawn_wins = drawn_result[1] or 0
            drawn_wr = (drawn_wins / drawn_games) if drawn_games > 0 else None
            
            # Calculate overall win rate (average of gih_wr and drawn_wr)
            # Only calculate if both metrics have sufficient sample size
            overall_wr = None
            if gih_wr is not None and drawn_wr is not None:
                if gih_games > 0 and drawn_games > 0:
                    overall_wr = (gih_wr + drawn_wr) / 2
                elif gih_games > 0:
                    overall_wr = gih_wr
                elif drawn_games > 0:
                    overall_wr = drawn_wr
            elif gih_wr is not None and gih_games > 0:
                overall_wr = gih_wr
            elif drawn_wr is not None and drawn_games > 0:
                overall_wr = drawn_wr
            
            # Calculate pick statistics
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_picks,
                    AVG(pick_number) as avg_pick_number,
                    AVG(pack_number) as avg_pack_number,
                    AVG(maindeck_rate) as maindeck_rate,
                    AVG(sideboard_rate) as sideboard_rate
                FROM draft_picks
                WHERE card_id = ? AND "set" = ?
            """, (card_id, set_code))
            pick_result = self.cursor.fetchone()
            total_picks = pick_result[0] or 0
            avg_pick_number = pick_result[1]
            avg_pack_number = pick_result[2]
            maindeck_rate = pick_result[3]
            sideboard_rate = pick_result[4]
            
            # Calculate total games and wins
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) as total_wins
                FROM game_cards gc
                JOIN game_results gr ON gc.game_id = gr.game_id
                WHERE gc.card_id = ? AND gr."set" = ?
            """, (card_id, set_code))
            game_result = self.cursor.fetchone()
            total_games = game_result[0] or 0
            total_wins = game_result[1] or 0
            total_losses = total_games - total_wins
            
            # Calculate ever_drawn_wr (win rate when card was ever drawn)
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as ever_drawn_games,
                    SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) as ever_drawn_wins
                FROM game_cards gc
                JOIN game_results gr ON gc.game_id = gr.game_id
                WHERE gc.card_id = ? 
                  AND (gc.was_drawn = 1 OR gc.in_opening_hand = 1)
                  AND gr."set" = ?
            """, (card_id, set_code))
            ever_drawn_result = self.cursor.fetchone()
            ever_drawn_games = ever_drawn_result[0] or 0
            ever_drawn_wins = ever_drawn_result[1] or 0
            ever_drawn_wr = (ever_drawn_wins / ever_drawn_games) if ever_drawn_games > 0 else None
            
            # Calculate maindeck_wr (win rate when card was in maindeck)
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as maindeck_games,
                    SUM(CASE WHEN gr.won = 1 THEN 1 ELSE 0 END) as maindeck_wins
                FROM game_cards gc
                JOIN game_results gr ON gc.game_id = gr.game_id
                WHERE gc.card_id = ? 
                  AND gc.in_maindeck = 1
                  AND gr."set" = ?
            """, (card_id, set_code))
            maindeck_result = self.cursor.fetchone()
            maindeck_games = maindeck_result[0] or 0
            maindeck_wins = maindeck_result[1] or 0
            maindeck_wr = (maindeck_wins / maindeck_games) if maindeck_games > 0 else None
            
            # Get event_type (use most common one)
            self.cursor.execute("""
                SELECT event_type, COUNT(*) as cnt
                FROM draft_picks
                WHERE card_id = ? AND "set" = ?
                GROUP BY event_type
                ORDER BY cnt DESC
                LIMIT 1
            """, (card_id, set_code))
            event_result = self.cursor.fetchone()
            event_type = event_result[0] if event_result else None
            
            # Insert statistics
            self.cursor.execute("""
                INSERT INTO card_statistics (
                    card_id, "set", event_type,
                    gih_wr, gih_games, gih_wins,
                    drawn_wr, drawn_games, drawn_wins,
                    overall_wr,
                    ever_drawn_wr,
                    maindeck_wr,
                    avg_pick_number, avg_pack_number, total_picks,
                    total_games, total_wins, total_losses,
                    maindeck_rate, sideboard_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                card_id, set_code, event_type,
                gih_wr, gih_games, gih_wins,
                drawn_wr, drawn_games, drawn_wins,
                overall_wr,
                ever_drawn_wr,
                maindeck_wr,
                avg_pick_number, avg_pack_number, total_picks,
                total_games, total_wins, total_losses,
                maindeck_rate, sideboard_rate
            ))
        
        self.conn.commit()
        print("[OK] Card statistics calculated")
        
    def calculate_archetype_statistics(self, set_code: str):
        """Calculate color archetype statistics."""
        print(f"\nCalculating archetype statistics for {set_code}...")
        
        # Delete existing archetype stats for this set
        self.cursor.execute('DELETE FROM color_archetypes WHERE "set" = ?', (set_code,))
        
        # Get unique color combinations
        self.cursor.execute("""
            SELECT DISTINCT main_colors, splash_colors, event_type
            FROM game_results
            WHERE "set" = ? AND main_colors IS NOT NULL AND main_colors != ''
        """, (set_code,))
        
        archetypes = self.cursor.fetchall()
        print(f"  Found {len(archetypes)} unique archetypes")
        
        for main_colors, splash_colors, event_type in tqdm(archetypes, desc="Calculating archetypes"):
            splash_colors = splash_colors or ''
            full_colors = main_colors + splash_colors if splash_colors else main_colors
            
            # Calculate statistics
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as total_wins,
                    AVG(num_turns) as avg_turns,
                    AVG(CASE WHEN on_play = 1 AND won = 1 THEN 1.0 ELSE 0.0 END) / 
                    NULLIF(SUM(CASE WHEN on_play = 1 THEN 1 ELSE 0 END), 0) as on_play_wr,
                    AVG(CASE WHEN on_play = 0 AND won = 1 THEN 1.0 ELSE 0.0 END) / 
                    NULLIF(SUM(CASE WHEN on_play = 0 THEN 1 ELSE 0 END), 0) as on_draw_wr,
                    AVG(num_mulligans) as avg_mulligans
                FROM game_results
                WHERE "set" = ? AND main_colors = ? 
                  AND COALESCE(splash_colors, '') = ?
            """, (set_code, main_colors, splash_colors))
            
            result = self.cursor.fetchone()
            if result and result[0] > 0:
                total_games = result[0]
                total_wins = result[1] or 0
                total_losses = total_games - total_wins
                win_rate = (total_wins / total_games) if total_games > 0 else None
                avg_turns = result[2]
                on_play_wr = result[3]
                on_draw_wr = result[4]
                avg_mulligans = result[5]
                
                # Check if archetype already exists (handle uniqueness manually since COALESCE not allowed in UNIQUE)
                self.cursor.execute("""
                    SELECT archetype_id FROM color_archetypes
                    WHERE "set" = ? AND event_type = ? AND main_colors = ? 
                      AND COALESCE(splash_colors, '') = ?
                """, (set_code, event_type, main_colors, splash_colors))
                existing = self.cursor.fetchone()
                
                if existing:
                    # Update existing record
                    self.cursor.execute("""
                        UPDATE color_archetypes SET
                            full_color_identity = ?,
                            total_games = ?,
                            total_wins = ?,
                            total_losses = ?,
                            win_rate = ?,
                            avg_num_turns = ?,
                            on_play_win_rate = ?,
                            on_draw_win_rate = ?,
                            avg_mulligans = ?,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE archetype_id = ?
                    """, (full_colors, total_games, total_wins, total_losses, win_rate,
                          avg_turns, on_play_wr, on_draw_wr, avg_mulligans, existing[0]))
                else:
                    # Insert new record
                    self.cursor.execute("""
                        INSERT INTO color_archetypes (
                            "set", event_type, main_colors, splash_colors, full_color_identity,
                            total_games, total_wins, total_losses, win_rate,
                            avg_num_turns, on_play_win_rate, on_draw_win_rate, avg_mulligans
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        set_code, event_type, main_colors, splash_colors, full_colors,
                        total_games, total_wins, total_losses, win_rate,
                        avg_turns, on_play_wr, on_draw_wr, avg_mulligans
                    ))
        
        self.conn.commit()
        print("[OK] Archetype statistics calculated")
        
    def calculate_draft_summaries(self, set_code: str):
        """Calculate draft-level summaries."""
        print(f"\nCalculating draft summaries for {set_code}...")
        
        # Delete existing summaries for this set
        self.cursor.execute('DELETE FROM draft_summaries WHERE "set" = ?', (set_code,))
        
        # Get unique drafts
        self.cursor.execute("""
            SELECT DISTINCT draft_id
            FROM draft_picks
            WHERE "set" = ?
        """, (set_code,))
        
        draft_ids = [row[0] for row in self.cursor.fetchall()]
        print(f"  Found {len(draft_ids)} unique drafts")
        
        for draft_id in tqdm(draft_ids, desc="Processing drafts"):
            # Get draft info from picks
            self.cursor.execute("""
                SELECT event_type, draft_time, rank
                FROM draft_picks
                WHERE draft_id = ?
                LIMIT 1
            """, (draft_id,))
            draft_info = self.cursor.fetchone()
            if not draft_info:
                continue
            
            event_type, draft_time, rank = draft_info
            
            # Get game statistics
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN won = 1 THEN 1 ELSE 0 END) as total_wins,
                    AVG(num_turns) as avg_turns,
                    main_colors, splash_colors
                FROM game_results
                WHERE draft_id = ?
                GROUP BY main_colors, splash_colors
                ORDER BY total_games DESC
                LIMIT 1
            """, (draft_id,))
            
            game_info = self.cursor.fetchone()
            if game_info:
                total_games = game_info[0] or 0
                total_wins = game_info[1] or 0
                total_losses = total_games - total_wins
                win_rate = (total_wins / total_games) if total_games > 0 else None
                avg_turns = game_info[2]
                final_colors = game_info[3] or ''
                splash_colors = game_info[4] or ''
            else:
                total_games = 0
                total_wins = 0
                total_losses = 0
                win_rate = None
                avg_turns = None
                final_colors = ''
                splash_colors = ''
            
            # Count picks
            self.cursor.execute("""
                SELECT COUNT(*) FROM draft_picks WHERE draft_id = ?
            """, (draft_id,))
            total_picks = self.cursor.fetchone()[0] or 0
            
            self.cursor.execute("""
                INSERT INTO draft_summaries (
                    draft_id, "set", event_type, draft_time, rank,
                    final_colors, splash_colors,
                    total_games, total_wins, total_losses, win_rate,
                    avg_game_length, total_picks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                draft_id, set_code, event_type, draft_time, rank,
                final_colors, splash_colors,
                total_games, total_wins, total_losses, win_rate,
                avg_turns, total_picks
            ))
        
        self.conn.commit()
        print("[OK] Draft summaries calculated")
        
    def delete_set_data(self, set_code: str):
        """Delete all data for a specific set (for overwriting)."""
        print(f"\nDeleting existing data for set {set_code}...")
        
        # Delete in order to respect foreign keys
        self.cursor.execute('DELETE FROM game_cards WHERE game_id IN (SELECT game_id FROM game_results WHERE "set" = ?)', (set_code,))
        self.cursor.execute('DELETE FROM game_results WHERE "set" = ?', (set_code,))
        self.cursor.execute('DELETE FROM draft_picks WHERE "set" = ?', (set_code,))
        self.cursor.execute('DELETE FROM draft_summaries WHERE "set" = ?', (set_code,))
        self.cursor.execute('DELETE FROM card_statistics WHERE "set" = ?', (set_code,))
        self.cursor.execute('DELETE FROM color_archetypes WHERE "set" = ?', (set_code,))
        self.cursor.execute('DELETE FROM cards WHERE "set" = ?', (set_code,))
        
        self.conn.commit()
        print(f"[OK] Deleted all data for set {set_code}")
        
    def run_pipeline(self, set_name: str, draft_data: str, game_data: str):
        """
        Run the complete pipeline.
        
        Args:
            set_name: Set code as 3-letter string (e.g., "TLA", "MOM", "BRO")
            draft_data: Path to draft data Parquet file
            game_data: Path to game data Parquet file
        """
        # Validate set_name is 3 letters
        if not set_name or len(set_name) != 3 or not set_name.isalpha():
            raise ValueError(f"set_name must be a 3-letter string, got: {set_name}")
        
        set_code = set_name.upper()
        
        # Validate files exist
        if not os.path.exists(draft_data):
            raise FileNotFoundError(f"Draft data file not found: {draft_data}")
        if not os.path.exists(game_data):
            raise FileNotFoundError(f"Game data file not found: {game_data}")
        
        print("=" * 60)
        print("MTG Draft Data Pipeline")
        print("=" * 60)
        print(f"Set: {set_code}")
        print(f"Draft Data: {draft_data}")
        print(f"Game Data: {game_data}")
        print("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Connect to database
            self.connect_db()
            
            # Create schema
            self.create_schema()
            
            # Delete existing data for this set (always overwrite)
            self.delete_set_data(set_code)
            
            # Process draft data
            self.process_draft_data(draft_data, set_code)
            
            # Process game data
            self.process_game_data(game_data, set_code)
            
            # Calculate statistics
            self.calculate_card_statistics(set_code)
            self.calculate_archetype_statistics(set_code)
            self.calculate_draft_summaries(set_code)
            
            # Final commit
            self.conn.commit()
            
            elapsed = datetime.now() - start_time
            print("\n" + "=" * 60)
            print("[OK] Pipeline completed successfully!")
            print(f"  Time elapsed: {elapsed}")
            print(f"  Database: {self.db_path}")
            print("=" * 60)
            
        except Exception as e:
            self.conn.rollback()
            print(f"\n[ERROR] Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.close_db()


def main():
    """Main entry point for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='MTG Draft Data Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mtg_draft_pipeline.py TLA draft_data.parquet game_data.parquet
  python mtg_draft_pipeline.py MOM draft_data.parquet game_data.parquet --db custom.db
        """
    )
    parser.add_argument('set_name', help='Set code as 3-letter string (e.g., TLA, MOM, BRO)')
    parser.add_argument('draft_data', help='Path to draft data Parquet file')
    parser.add_argument('game_data', help='Path to game data Parquet file')
    parser.add_argument('--db', default='mtg_draft_coach.db', help='SQLite database path (default: mtg_draft_coach.db)')
    parser.add_argument('--no-scryfall', action='store_true', help='Skip Scryfall API calls (faster but less complete metadata)')
    
    args = parser.parse_args()
    
    # Validate set_name
    if len(args.set_name) != 3 or not args.set_name.isalpha():
        parser.error(f"set_name must be a 3-letter string, got: {args.set_name}")
    
    pipeline = MTGDraftPipeline(
        db_path=args.db,
        use_scryfall=not args.no_scryfall
    )
    
    pipeline.run_pipeline(
        set_name=args.set_name,
        draft_data=args.draft_data,
        game_data=args.game_data
    )


if __name__ == "__main__":
    main()

