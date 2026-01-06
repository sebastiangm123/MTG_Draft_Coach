"""
Optimized 17Lands Draft Data Processor
Best practices for processing large CSV files with memory efficiency and progress tracking.
"""

import csv
import sqlite3
import os
import re
import time
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


class OptimizedDraftDataProcessor:
    """Optimized processor for large CSV files with best practices."""
    
    SCRYFALL_API_BASE = "https://api.scryfall.com"
    
    def __init__(self, db_path: str = "draft_data.db", max_workers: int = 5):
        """
        Initialize the processor.
        
        Args:
            db_path: Path to SQLite database file
            max_workers: Number of threads for parallel API calls
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.card_metadata_cache: Dict[str, Dict] = {}
        self.cache_lock = Lock()
        self.scryfall_session = requests.Session()
        self.scryfall_session.headers.update({
            'User-Agent': 'MTG-Draft-Coach/1.0'
        })
        self.max_workers = max_workers
        self.checkpoint_file = f"{db_path}.checkpoint"
    
    def connect(self):
        """Connect to SQLite database with optimizations."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Enable WAL mode for better concurrency and performance
        self.cursor.execute("PRAGMA journal_mode = WAL")
        
        # Optimize for bulk inserts
        self.cursor.execute("PRAGMA synchronous = NORMAL")
        self.cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
        self.cursor.execute("PRAGMA temp_store = MEMORY")
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
    
    def load_checkpoint(self) -> Set[tuple]:
        """Load processed cards from checkpoint file."""
        if not os.path.exists(self.checkpoint_file):
            return set()
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(tuple(item) for item in data)
        except Exception as e:
            print(f"Warning: Could not load checkpoint: {e}")
            return set()
    
    def save_checkpoint(self, processed_cards: Set[tuple]):
        """Save processed cards to checkpoint file."""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(list(processed_cards), f)
        except Exception as e:
            print(f"Warning: Could not save checkpoint: {e}")
    
    def parse_mana_cost(self, mana_cost: str) -> tuple:
        """Parse mana cost to extract CMC and color identity."""
        if not mana_cost or mana_cost == "None" or mana_cost == "":
            return None, ""
        
        cost_parts = re.findall(r'\{([^}]+)\}', mana_cost)
        cmc = 0
        colors = set()
        has_variable = False
        
        for part in cost_parts:
            part_upper = part.upper()
            
            if '/' in part:
                hybrid_parts = part_upper.split('/')
                hybrid_cmc = 0
                for hp in hybrid_parts:
                    if hp in ['W', 'U', 'B', 'R', 'G']:
                        colors.add(hp)
                        hybrid_cmc = max(hybrid_cmc, 1)
                    elif hp.isdigit():
                        hybrid_cmc = max(hybrid_cmc, int(hp))
                cmc += hybrid_cmc if hybrid_cmc > 0 else 1
            elif part_upper in ['W', 'U', 'B', 'R', 'G']:
                colors.add(part_upper)
                cmc += 1
            elif part_upper == 'C':
                cmc += 1
            elif part.isdigit():
                cmc += int(part)
            elif part_upper in ['X', 'Y', 'Z']:
                has_variable = True
            elif part_upper.startswith('P'):
                color_part = part_upper.replace('P', '')
                if color_part in ['W', 'U', 'B', 'R', 'G']:
                    colors.add(color_part)
                cmc += 1
            elif part_upper == 'S':
                cmc += 1
            else:
                numbers = re.findall(r'\d+', part)
                if numbers:
                    cmc += sum(int(n) for n in numbers)
        
        if has_variable:
            cmc = None
        
        color_order = ['W', 'U', 'B', 'R', 'G']
        color_identity = ''.join([c for c in color_order if c in colors])
        
        return cmc, color_identity
    
    def get_card_from_scryfall(self, card_name: str, set_code: str) -> Optional[Dict]:
        """Fetch card metadata from Scryfall API (thread-safe)."""
        cache_key = f"{set_code}:{card_name.lower()}"
        
        # Check cache (thread-safe)
        with self.cache_lock:
            if cache_key in self.card_metadata_cache:
                return self.card_metadata_cache[cache_key]
        
        try:
            search_query = f'!"{card_name}" set:{set_code.lower()}'
            response = self.scryfall_session.get(
                f"{self.SCRYFALL_API_BASE}/cards/search",
                params={'q': search_query},
                timeout=10
            )
            time.sleep(0.1)  # Rate limiting
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
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
                    
                    with self.cache_lock:
                        self.card_metadata_cache[cache_key] = metadata
                    return metadata
            
            # Fallback: search without set
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
                            
                            with self.cache_lock:
                                self.card_metadata_cache[cache_key] = metadata
                            return metadata
                    
                    # Use first result if no set match
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
                    
                    with self.cache_lock:
                        self.card_metadata_cache[cache_key] = metadata
                    return metadata
        
        except Exception as e:
            pass  # Silent fail, will be handled by caller
        
        with self.cache_lock:
            self.card_metadata_cache[cache_key] = None
        return None
    
    def fetch_card_metadata_batch(self, cards: List[tuple]) -> Dict[tuple, Dict]:
        """Fetch metadata for a batch of cards in parallel."""
        results = {}
        
        def fetch_one(card_tuple):
            expansion, card_name = card_tuple
            metadata = self.get_card_from_scryfall(card_name, expansion)
            return card_tuple, metadata
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_card = {executor.submit(fetch_one, card): card for card in cards}
            
            for future in as_completed(future_to_card):
                try:
                    card_tuple, metadata = future.result()
                    results[card_tuple] = metadata
                except Exception as e:
                    card_tuple = future_to_card[future]
                    results[card_tuple] = None
        
        return results
    
    def process_csv_file_optimized(self, csv_file_path: str, 
                                  chunk_size: int = 1000,
                                  batch_size: int = 100,
                                  resume: bool = True):
        """
        Optimized CSV processing with progress tracking and error handling.
        
        Args:
            csv_file_path: Path to CSV file
            chunk_size: Number of cards to fetch in parallel
            batch_size: Number of records to insert per transaction
            resume: Whether to resume from checkpoint
        """
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
        
        self.connect()
        self.create_normalized_table()
        
        # Load checkpoint if resuming
        processed_cards = set()
        if resume:
            processed_cards = self.load_checkpoint()
            if processed_cards:
                print(f"Resuming: {len(processed_cards)} cards already processed")
        
        print(f"Processing CSV file: {csv_file_path}")
        
        # Pass 1: Collect unique cards (streaming, memory efficient)
        print("\n[Pass 1] Collecting unique cards...")
        unique_cards: Set[tuple] = set()
        row_count = 0
        error_count = 0
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        expansion = row.get('expansion', '').strip()
                        card_name = row.get('pick', '').strip()
                        
                        if expansion and card_name:
                            card_tuple = (expansion, card_name)
                            if card_tuple not in processed_cards:
                                unique_cards.add(card_tuple)
                        
                        row_count += 1
                        if row_count % 100000 == 0:
                            print(f"  Processed {row_count:,} rows, found {len(unique_cards):,} unique cards...")
                    except Exception as e:
                        error_count += 1
                        if error_count % 1000 == 0:
                            print(f"  Warning: {error_count} rows had errors (continuing...)")
                        continue
        
        except Exception as e:
            print(f"Error reading CSV: {e}")
            raise
        
        print(f"Found {len(unique_cards):,} unique cards across {row_count:,} picks")
        if error_count > 0:
            print(f"  ({error_count} rows had errors but were skipped)")
        
        if not unique_cards:
            print("No new cards to process!")
            return
        
        # Pass 2: Fetch metadata and insert (with progress tracking)
        print(f"\n[Pass 2] Fetching metadata for {len(unique_cards):,} cards...")
        
        unique_list = list(unique_cards)
        total_cards = len(unique_list)
        processed_count = len(processed_cards)
        success_count = 0
        failed_count = 0
        
        # Process in chunks
        for i in range(0, total_cards, chunk_size):
            chunk = unique_list[i:i + chunk_size]
            
            # Fetch metadata in parallel
            metadata_results = self.fetch_card_metadata_batch(chunk)
            
            # Prepare batch for insertion
            insert_batch = []
            
            for card_tuple in chunk:
                expansion, card_name = card_tuple
                normalized_name = card_name.lower()
                metadata = metadata_results.get(card_tuple)
                
                if metadata:
                    insert_batch.append((
                        expansion,
                        normalized_name,
                        None,  # GIH WR
                        metadata.get('color_identity', ''),
                        metadata.get('card_type', ''),
                        metadata.get('cmc')
                    ))
                    success_count += 1
                else:
                    insert_batch.append((
                        expansion,
                        normalized_name,
                        None,  # GIH WR
                        '',  # color_identity
                        '',  # card_type
                        None  # cmc
                    ))
                    failed_count += 1
            
            # Insert batch
            if insert_batch:
                self._insert_normalized_batch(insert_batch)
                processed_cards.update(chunk)
                processed_count += len(chunk)
                
                # Save checkpoint periodically
                if processed_count % (chunk_size * 5) == 0:
                    self.save_checkpoint(processed_cards)
                    self.conn.commit()
                
                # Progress update
                progress_pct = (processed_count / total_cards) * 100
                print(f"  Progress: {processed_count:,}/{total_cards:,} ({progress_pct:.1f}%) | "
                      f"Success: {success_count:,} | Failed: {failed_count:,}")
        
        # Final commit and checkpoint
        self.conn.commit()
        self.save_checkpoint(processed_cards)
        
        # Clean up checkpoint if processing complete
        if processed_count >= total_cards:
            try:
                os.remove(self.checkpoint_file)
                print("\n✓ Processing complete! Checkpoint file removed.")
            except:
                pass
        
        print(f"\n{'='*60}")
        print(f"Processing Summary:")
        print(f"  Total cards processed: {processed_count:,}")
        print(f"  Successfully fetched metadata: {success_count:,}")
        print(f"  Failed to fetch metadata: {failed_count:,}")
        print(f"  Note: GIH WR is NULL and needs to be populated separately")
    
    def _insert_normalized_batch(self, batch: List[tuple]):
        """Insert a batch of normalized card records."""
        self.cursor.executemany("""
            INSERT OR REPLACE INTO normalized_cards 
            (set, card_name, gih_wr, color_identity, card_type, cmc)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
    
    def get_card(self, card_name: str, set_code: Optional[str] = None) -> Optional[Dict]:
        """Get normalized card data."""
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


# Example usage
if __name__ == "__main__":
    processor = OptimizedDraftDataProcessor("draft_data.db", max_workers=5)
    
    csv_file = "draft_data_public.TLA.PremierDraft.csv"
    
    if os.path.exists(csv_file):
        processor.process_csv_file_optimized(
            csv_file,
            chunk_size=50,  # Fetch 50 cards in parallel
            batch_size=100,  # Insert 100 records per transaction
            resume=True  # Resume from checkpoint if interrupted
        )
        processor.close()
    else:
        print(f"CSV file not found: {csv_file}")

