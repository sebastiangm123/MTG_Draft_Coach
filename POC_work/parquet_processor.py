"""
Parquet-based Draft Data Processor
Converts CSV to Parquet and processes with optimized performance.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
from pathlib import Path
from typing import Dict, List, Optional
import time
import requests
import re


class ParquetDraftProcessor:
    """Processes draft data using Parquet format for optimal performance."""
    
    SCRYFALL_API_BASE = "https://api.scryfall.com"
    
    def __init__(self):
        self.scryfall_session = requests.Session()
        self.scryfall_session.headers.update({
            'User-Agent': 'MTG-Draft-Coach/1.0'
        })
        self.card_metadata_cache: Dict[str, Dict] = {}
    
    def csv_to_parquet(self, csv_path: str, parquet_path: Optional[str] = None,
                      chunk_size: int = 100000, compression: str = 'snappy'):
        """
        Convert CSV file to Parquet format.
        
        Args:
            csv_path: Path to CSV file
            parquet_path: Output Parquet path (default: same name with .parquet extension)
            chunk_size: Rows to process per chunk
            compression: Compression codec ('snappy', 'gzip', 'brotli', 'zstd')
        
        Returns:
            Path to created Parquet file
        """
        if parquet_path is None:
            parquet_path = csv_path.replace('.csv', '.parquet')
        
        print(f"Converting {csv_path} to Parquet format...")
        print(f"  Output: {parquet_path}")
        print(f"  Compression: {compression}")
        
        # Get file size for progress
        csv_size = os.path.getsize(csv_path) / (1024 * 1024)  # MB
        print(f"  Input size: {csv_size:.1f} MB")
        
        # Read CSV in chunks and write to Parquet
        first_chunk = True
        total_rows = 0
        start_time = time.time()
        
        parquet_writer = None
        
        try:
            for chunk_num, chunk_df in enumerate(pd.read_csv(csv_path, chunksize=chunk_size, 
                                                          low_memory=False, encoding='utf-8')):
                total_rows += len(chunk_df)
                
                # Convert to PyArrow table
                table = pa.Table.from_pandas(chunk_df)
                
                # Write first chunk (creates file)
                if first_chunk:
                    pq.write_table(table, parquet_path, compression=compression)
                    first_chunk = False
                else:
                    # Append to existing file
                    parquet_file = pq.ParquetFile(parquet_path)
                    existing_table = parquet_file.read()
                    combined_table = pa.concat_tables([existing_table, table])
                    pq.write_table(combined_table, parquet_path, compression=compression)
                
                elapsed = time.time() - start_time
                rate = total_rows / elapsed if elapsed > 0 else 0
                print(f"  Processed {total_rows:,} rows ({rate:,.0f} rows/sec)...", end='\r')
            
            # Get output size
            parquet_size = os.path.getsize(parquet_path) / (1024 * 1024)  # MB
            compression_ratio = csv_size / parquet_size if parquet_size > 0 else 1
            
            print(f"\n✓ Conversion complete!")
            print(f"  Total rows: {total_rows:,}")
            print(f"  Output size: {parquet_size:.1f} MB")
            print(f"  Compression ratio: {compression_ratio:.1f}x smaller")
            print(f"  Time: {time.time() - start_time:.1f} seconds")
            
            return parquet_path
        
        except Exception as e:
            print(f"\n✗ Error during conversion: {e}")
            if os.path.exists(parquet_path):
                os.remove(parquet_path)
            raise
    
    def read_parquet(self, parquet_path: str, columns: Optional[List[str]] = None,
                    filters: Optional[List] = None) -> pd.DataFrame:
        """
        Read Parquet file with optional column selection and filtering.
        
        Args:
            parquet_path: Path to Parquet file
            columns: List of columns to read (None = all columns)
            filters: PyArrow filter expressions for predicate pushdown
        
        Returns:
            DataFrame with selected data
        """
        return pd.read_parquet(parquet_path, columns=columns, filters=filters)
    
    def get_unique_cards(self, parquet_path: str) -> pd.DataFrame:
        """
        Get unique cards from Parquet file (only reads needed columns).
        
        Args:
            parquet_path: Path to Parquet file
        
        Returns:
            DataFrame with unique (expansion, pick) combinations
        """
        print("Reading unique cards from Parquet...")
        
        # Only read the columns we need (much faster!)
        df = pd.read_parquet(parquet_path, columns=['expansion', 'pick'])
        
        # Get unique combinations
        unique_cards = df[['expansion', 'pick']].drop_duplicates()
        unique_cards = unique_cards[unique_cards['pick'].notna()]
        unique_cards = unique_cards[unique_cards['expansion'].notna()]
        
        print(f"Found {len(unique_cards):,} unique cards")
        return unique_cards
    
    def query_cards(self, parquet_path: str, 
                   card_name: Optional[str] = None,
                   expansion: Optional[str] = None,
                   columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Query cards from Parquet file with filters.
        
        Args:
            parquet_path: Path to Parquet file
            card_name: Filter by card name (case-insensitive partial match)
            expansion: Filter by expansion
            columns: Columns to return (None = all)
        
        Returns:
            Filtered DataFrame
        """
        filters = []
        
        if expansion:
            filters.append(('expansion', '==', expansion))
        
        if card_name:
            # Note: Parquet predicate pushdown works best with exact matches
            # For partial matches, we'll filter after reading
            df = pd.read_parquet(parquet_path, columns=columns, filters=filters if filters else None)
            if card_name:
                df = df[df['pick'].str.contains(card_name, case=False, na=False)]
        else:
            df = pd.read_parquet(parquet_path, columns=columns, filters=filters if filters else None)
        
        return df
    
    def create_normalized_parquet(self, source_parquet: str, output_parquet: str,
                                 scryfall_batch_size: int = 50):
        """
        Create normalized Parquet file with card metadata.
        
        Args:
            source_parquet: Source Parquet file with draft picks
            output_parquet: Output Parquet file for normalized data
            scryfall_batch_size: Cards to fetch from Scryfall per batch
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        print("Creating normalized Parquet dataset...")
        
        # Get unique cards
        unique_cards_df = self.get_unique_cards(source_parquet)
        
        # Fetch metadata from Scryfall (parallel)
        print(f"Fetching metadata for {len(unique_cards_df):,} cards from Scryfall...")
        
        def fetch_metadata(row):
            expansion, card_name = row['expansion'], row['pick']
            return self._get_card_metadata(card_name, expansion)
        
        metadata_list = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_metadata, row): row 
                      for _, row in unique_cards_df.iterrows()}
            
            for future in as_completed(futures):
                row = futures[future]
                try:
                    metadata = future.result()
                    metadata_list.append({
                        'set': row['expansion'],
                        'card_name': row['pick'].lower(),
                        'gih_wr': None,  # To be populated separately
                        'color_identity': metadata.get('color_identity', '') if metadata else '',
                        'card_type': metadata.get('card_type', '') if metadata else '',
                        'cmc': metadata.get('cmc') if metadata else None
                    })
                except Exception as e:
                    metadata_list.append({
                        'set': row['expansion'],
                        'card_name': row['pick'].lower(),
                        'gih_wr': None,
                        'color_identity': '',
                        'card_type': '',
                        'cmc': None
                    })
        
        # Create DataFrame and save to Parquet
        normalized_df = pd.DataFrame(metadata_list)
        normalized_df.to_parquet(output_parquet, compression='snappy', index=False)
        
        print(f"✓ Normalized Parquet created: {output_parquet}")
        print(f"  Records: {len(normalized_df):,}")
        
        return output_parquet
    
    def _get_card_metadata(self, card_name: str, set_code: str) -> Optional[Dict]:
        """Fetch card metadata from Scryfall (simplified version)."""
        cache_key = f"{set_code}:{card_name.lower()}"
        if cache_key in self.card_metadata_cache:
            return self.card_metadata_cache[cache_key]
        
        try:
            search_query = f'!"{card_name}" set:{set_code.lower()}'
            response = self.scryfall_session.get(
                f"{self.SCRYFALL_API_BASE}/cards/search",
                params={'q': search_query},
                timeout=10
            )
            time.sleep(0.1)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    card = data['data'][0]
                    mana_cost = card.get('mana_cost', '')
                    cmc, color_identity = self._parse_mana_cost(mana_cost)
                    
                    metadata = {
                        'color_identity': color_identity,
                        'card_type': card.get('type_line', ''),
                        'cmc': cmc if cmc is not None else card.get('cmc')
                    }
                    
                    self.card_metadata_cache[cache_key] = metadata
                    return metadata
        except:
            pass
        
        self.card_metadata_cache[cache_key] = None
        return None
    
    def _parse_mana_cost(self, mana_cost: str) -> tuple:
        """Parse mana cost (simplified version)."""
        if not mana_cost or mana_cost == "None":
            return None, ""
        
        cost_parts = re.findall(r'\{([^}]+)\}', mana_cost)
        cmc = 0
        colors = set()
        
        for part in cost_parts:
            part_upper = part.upper()
            if '/' in part:
                hybrid_parts = part_upper.split('/')
                for hp in hybrid_parts:
                    if hp in ['W', 'U', 'B', 'R', 'G']:
                        colors.add(hp)
                cmc += 1
            elif part_upper in ['W', 'U', 'B', 'R', 'G']:
                colors.add(part_upper)
                cmc += 1
            elif part.isdigit():
                cmc += int(part)
        
        color_order = ['W', 'U', 'B', 'R', 'G']
        color_identity = ''.join([c for c in color_order if c in colors])
        
        return cmc, color_identity
    
    def get_statistics(self, parquet_path: str) -> Dict:
        """Get file statistics."""
        parquet_file = pq.ParquetFile(parquet_path)
        metadata = parquet_file.metadata
        
        return {
            'num_rows': metadata.num_rows,
            'num_columns': len(metadata.schema),
            'file_size_mb': os.path.getsize(parquet_path) / (1024 * 1024),
            'compression': metadata.row_group(0).column(0).compression,
            'schema': [field.name for field in metadata.schema]
        }


# Example usage
if __name__ == "__main__":
    processor = ParquetDraftProcessor()
    
    csv_file = "draft_data_public.TLA.PremierDraft.csv"
    parquet_file = "draft_data_public.TLA.PremierDraft.parquet"
    
    if os.path.exists(csv_file):
        # Convert CSV to Parquet (one-time operation)
        if not os.path.exists(parquet_file):
            processor.csv_to_parquet(csv_file, parquet_file)
        
        # Get statistics
        stats = processor.get_statistics(parquet_file)
        print(f"\nParquet file statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Example: Query specific cards (fast!)
        print("\nQuerying cards with 'Sokka' in name...")
        results = processor.query_cards(parquet_file, card_name="Sokka", 
                                        columns=['expansion', 'pick', 'rank'])
        print(f"Found {len(results)} matching picks")
        print(results.head())
        
        # Example: Get unique cards (only reads 2 columns!)
        unique_cards = processor.get_unique_cards(parquet_file)
        print(f"\nUnique cards: {len(unique_cards)}")
        
    else:
        print(f"CSV file not found: {csv_file}")

