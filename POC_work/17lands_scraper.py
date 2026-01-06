"""
17Lands Draft Data Processor
Processes 17Lands draft data CSV files and creates a normalized SQLite database.
"""

import csv
import sqlite3
import os
import re
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict


class DraftDataProcessor:
    """Processes 17Lands draft data CSV files into normalized SQLite database."""
    
    SCRYFALL_API_BASE = "https://api.scryfall.com"
    
    def __init__(self, db_path: str = "draft_data.db"):
        """
        Initialize the processor.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.card_metadata_cache: Dict[str, Dict] = {}
        self.scryfall_session = requests.Session()
        self.scryfall_session.headers.update({
            'User-Agent': 'MTG-Draft-Coach/1.0'
        })
    
    def connect(self):
        """Connect to SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def create_normalized_table(self):
        """Create normalized card data table with requested schema."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS normalized_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set TEXT NOT NULL,
                card_name TEXT NOT NULL,
                gih_wr REAL,
                color_identity TEXT,
                card_type TEXT,
                cmc INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(set, card_name)
            )
        """)
        
        # Indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_normalized_set ON normalized_cards(set)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_normalized_name ON normalized_cards(card_name)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_normalized_color ON normalized_cards(color_identity)")
        
        self.conn.commit()
        print("Normalized table created successfully.")
    
    def parse_mana_cost(self, mana_cost: str) -> tuple:
        """
        Parse mana cost to extract CMC and color identity.
        
        Args:
            mana_cost: Mana cost string (e.g., "{2}{U}{B}", "{G}", "{X}{R}", "{W/U}")
        
        Returns:
            Tuple of (cmc, color_identity)
            cmc: Converted mana cost (integer, None if X or invalid)
            color_identity: Color identity string in WUBRG order (each color appears once)
        """
        if not mana_cost or mana_cost == "None" or mana_cost == "":
            return None, ""
        
        # Remove curly braces and split
        cost_parts = re.findall(r'\{([^}]+)\}', mana_cost)
        
        cmc = 0
        colors = set()
        has_variable = False
        
        for part in cost_parts:
            part_upper = part.upper()
            
            # Handle hybrid mana (e.g., {W/U}, {2/B})
            if '/' in part:
                # Split hybrid mana
                hybrid_parts = part_upper.split('/')
                hybrid_cmc = 0
                for hp in hybrid_parts:
                    if hp in ['W', 'U', 'B', 'R', 'G']:
                        colors.add(hp)
                        hybrid_cmc = max(hybrid_cmc, 1)  # At least 1 if has color
                    elif hp.isdigit():
                        hybrid_cmc = max(hybrid_cmc, int(hp))
                # Each hybrid symbol counts as 1 CMC (or the numeric value if present)
                cmc += hybrid_cmc if hybrid_cmc > 0 else 1
            elif part_upper in ['W', 'U', 'B', 'R', 'G']:
                colors.add(part_upper)
                cmc += 1  # Each colored mana symbol counts as 1 CMC
            elif part_upper == 'C':
                # Colorless mana - counts toward CMC but not color identity
                cmc += 1
            elif part.isdigit():
                cmc += int(part)
            elif part_upper in ['X', 'Y', 'Z']:
                has_variable = True
                # Variable cost - we'll set CMC to None
            elif part_upper.startswith('P'):  # Phyrexian mana
                # Extract the color from phyrexian mana (e.g., {W/P})
                color_part = part_upper.replace('P', '')
                if color_part in ['W', 'U', 'B', 'R', 'G']:
                    colors.add(color_part)
                cmc += 1
            elif part_upper == 'S':  # Snow mana
                cmc += 1
            else:
                # Unknown symbol - try to extract numbers
                numbers = re.findall(r'\d+', part)
                if numbers:
                    cmc += sum(int(n) for n in numbers)
        
        # If there's a variable cost, CMC is None
        if has_variable:
            cmc = None
        
        # Build color identity in WUBRG order (each color appears only once)
        color_order = ['W', 'U', 'B', 'R', 'G']
        color_identity = ''.join([c for c in color_order if c in colors])
        
        return cmc, color_identity
    
    def get_card_from_scryfall(self, card_name: str, set_code: str) -> Optional[Dict]:
        """
        Fetch card metadata from Scryfall API.
        
        Args:
            card_name: Name of the card
            set_code: Set code (e.g., "TLA")
        
        Returns:
            Dictionary with card metadata or None if not found
        """
        # Check cache first
        cache_key = f"{set_code}:{card_name.lower()}"
        if cache_key in self.card_metadata_cache:
            return self.card_metadata_cache[cache_key]
        
        try:
            # Search for card by name and set
            # Scryfall uses set codes, need to map 17Lands set codes to Scryfall
            # For now, try direct search
            search_query = f'!"{card_name}" set:{set_code.lower()}'
            
            response = self.scryfall_session.get(
                f"{self.SCRYFALL_API_BASE}/cards/search",
                params={'q': search_query},
                timeout=10
            )
            
            # Rate limiting - be nice to Scryfall
            time.sleep(0.1)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    card = data['data'][0]
                    
                    # Extract needed information
                    mana_cost = card.get('mana_cost', '')
                    cmc, color_identity = self.parse_mana_cost(mana_cost)
                    
                    # Get card type
                    card_type = card.get('type_line', '')
                    
                    metadata = {
                        'name': card.get('name', card_name),
                        'mana_cost': mana_cost,
                        'cmc': cmc if cmc is not None else card.get('cmc'),  # Fallback to Scryfall's CMC
                        'color_identity': color_identity,
                        'card_type': card_type,
                        'colors': card.get('colors', [])
                    }
                    
                    # Cache it
                    self.card_metadata_cache[cache_key] = metadata
                    return metadata
            
            # If search failed, try without set code
            search_query = f'!"{card_name}"'
            response = self.scryfall_session.get(
                f"{self.SCRYFALL_API_BASE}/cards/search",
                params={'q': search_query},
                timeout=10
            )
            time.sleep(0.1)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    # Try to find one from the right set
                    for card in data['data']:
                        if card.get('set', '').upper() == set_code.upper():
                            mana_cost = card.get('mana_cost', '')
                            cmc, color_identity = self.parse_mana_cost(mana_cost)
                            
                            metadata = {
                                'name': card.get('name', card_name),
                                'mana_cost': mana_cost,
                                'cmc': cmc if cmc is not None else card.get('cmc'),
                                'color_identity': color_identity,
                                'card_type': card.get('type_line', ''),
                                'colors': card.get('colors', [])
                            }
                            
                            self.card_metadata_cache[cache_key] = metadata
                            return metadata
                    
                    # If no set match, use first result
                    card = data['data'][0]
                    mana_cost = card.get('mana_cost', '')
                    cmc, color_identity = self.parse_mana_cost(mana_cost)
                    
                    metadata = {
                        'name': card.get('name', card_name),
                        'mana_cost': mana_cost,
                        'cmc': cmc if cmc is not None else card.get('cmc'),
                        'color_identity': color_identity,
                        'card_type': card.get('type_line', ''),
                        'colors': card.get('colors', [])
                    }
                    
                    self.card_metadata_cache[cache_key] = metadata
                    return metadata
        
        except Exception as e:
            print(f"Error fetching card '{card_name}' from Scryfall: {e}")
        
        # Cache None to avoid repeated failed requests
        self.card_metadata_cache[cache_key] = None
        return None
    
    def calculate_gih_wr(self, card_name: str, expansion: str, all_picks: List[Dict]) -> Optional[float]:
        """
        Calculate Game In Hand Win Rate for a card.
        
        Note: This is a simplified calculation. GIH WR typically requires
        tracking when a card was in hand at game start, which may not be
        directly available in this dataset.
        
        Args:
            card_name: Name of the card
            expansion: Set code
            all_picks: List of all pick records
        
        Returns:
            GIH WR as float (0-1) or None if cannot be calculated
        """
        # For now, return None as GIH WR calculation requires specific game state data
        # that may not be available in the draft pick CSV
        # This would need to be populated from a different data source or calculated
        # from game logs if available
        return None
    
    def process_csv_file(self, csv_file_path: str, chunk_size: int = 10000):
        """
        Process CSV file and create normalized dataset.
        
        Args:
            csv_file_path: Path to CSV file
            chunk_size: Number of rows to process before committing
        """
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
        
        self.connect()
        self.create_normalized_table()
        
        print(f"Processing CSV file: {csv_file_path}")
        
        # First pass: collect unique cards
        print("Pass 1: Collecting unique cards...")
        unique_cards: Set[tuple] = set()  # (set, card_name)
        row_count = 0
        
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                expansion = row.get('expansion', '').strip()
                card_name = row.get('pick', '').strip()
                
                if expansion and card_name:
                    unique_cards.add((expansion, card_name))
                
                row_count += 1
                if row_count % 100000 == 0:
                    print(f"  Processed {row_count} rows, found {len(unique_cards)} unique cards...")
        
        print(f"Found {len(unique_cards)} unique cards across {row_count} picks")
        
        # Second pass: fetch metadata and create normalized records
        print("\nPass 2: Fetching card metadata and creating normalized records...")
        processed = 0
        failed = 0
        
        batch = []
        
        for expansion, card_name in unique_cards:
            # Normalize card name to lowercase
            normalized_name = card_name.lower()
            
            # Get card metadata from Scryfall
            metadata = self.get_card_from_scryfall(card_name, expansion)
            
            if metadata:
                batch.append((
                    expansion,
                    normalized_name,
                    None,  # GIH WR - to be populated separately
                    metadata.get('color_identity', ''),
                    metadata.get('card_type', ''),
                    metadata.get('cmc')
                ))
                processed += 1
            else:
                # Still insert with NULL metadata
                batch.append((
                    expansion,
                    normalized_name,
                    None,  # GIH WR
                    '',  # color_identity
                    '',  # card_type
                    None  # cmc
                ))
                failed += 1
                if failed % 10 == 0:
                    print(f"  Warning: {failed} cards not found in Scryfall")
            
            # Insert batch periodically
            if len(batch) >= chunk_size:
                self._insert_normalized_batch(batch)
                batch = []
                print(f"  Processed {processed + failed}/{len(unique_cards)} cards...")
            
            # Rate limiting for Scryfall API
            if (processed + failed) % 50 == 0:
                time.sleep(1)  # Brief pause every 50 cards
        
        # Insert remaining batch
        if batch:
            self._insert_normalized_batch(batch)
        
        self.conn.commit()
        
        print(f"\nProcessing complete!")
        print(f"  Total unique cards: {len(unique_cards)}")
        print(f"  Successfully fetched metadata: {processed}")
        print(f"  Failed to fetch metadata: {failed}")
        print(f"\nNote: GIH WR is set to NULL and needs to be populated from game data.")
    
    def _insert_normalized_batch(self, batch: List[tuple]):
        """Insert a batch of normalized card records."""
        self.cursor.executemany("""
            INSERT OR REPLACE INTO normalized_cards 
            (set, card_name, gih_wr, color_identity, card_type, cmc)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
    
    def get_card(self, card_name: str, set_code: Optional[str] = None) -> Optional[Dict]:
        """
        Get normalized card data.
        
        Args:
            card_name: Card name (case insensitive)
            set_code: Optional set code filter
        
        Returns:
            Dictionary with card data or None
        """
        if not self.conn:
            self.connect()
        
        query = "SELECT * FROM normalized_cards WHERE card_name = LOWER(?)"
        params = [card_name]
        
        if set_code:
            query += " AND set = ?"
            params.append(set_code)
        
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        columns = [desc[0] for desc in self.cursor.description]
        return dict(zip(columns, row))
    
    def search_cards(self, query: str, set_code: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Search for cards by name.
        
        Args:
            query: Search query (partial card name)
            set_code: Optional set code filter
            limit: Maximum number of results
        
        Returns:
            List of matching card dictionaries
        """
        if not self.conn:
            self.connect()
        
        sql_query = "SELECT * FROM normalized_cards WHERE card_name LIKE ?"
        params = [f'%{query.lower()}%']
        
        if set_code:
            sql_query += " AND set = ?"
            params.append(set_code)
        
        sql_query += " LIMIT ?"
        params.append(limit)
        
        self.cursor.execute(sql_query, params)
        rows = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        
        return [dict(zip(columns, row)) for row in rows]


def main():
    """Example usage."""
    processor = DraftDataProcessor("draft_data.db")
    
    csv_file = "draft_data_public.TLA.PremierDraft.csv"
    
    if os.path.exists(csv_file):
        print(f"Processing {csv_file}...")
        processor.process_csv_file(csv_file, chunk_size=1000)
        
        # Example queries
        print("\n" + "="*60)
        print("Example: Get card data")
        card = processor.get_card("The Lion-Turtle", "TLA")
        if card:
            print(f"Card: {card['card_name']}")
            print(f"  Set: {card['set']}")
            print(f"  Color Identity: {card['color_identity']}")
            print(f"  CMC: {card['cmc']}")
            print(f"  Type: {card['card_type']}")
        
        processor.close()
    else:
        print(f"CSV file not found: {csv_file}")


if __name__ == "__main__":
    main()
