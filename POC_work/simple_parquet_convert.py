"""
Simple, robust CSV to Parquet converter.
Writes incrementally to avoid memory issues.
"""

import pandas as pd
import pyarrow.parquet as pq
import os

csv_file = "game_data_public.TLA.PremierDraft.csv"
parquet_file = csv_file.replace('.csv', '.parquet')

if not os.path.exists(csv_file):
    print(f"Error: {csv_file} not found!")
    exit(1)

csv_size = os.path.getsize(csv_file) / (1024 * 1024)
print(f"Converting {csv_file} to Parquet...")
print(f"  Size: {csv_size:.2f} MB")
print(f"  Processing in chunks...\n")

chunk_size = 10000  # Small chunks
total_rows = 0
first_chunk = True

try:
    for chunk_num, chunk_df in enumerate(pd.read_csv(csv_file, chunksize=chunk_size, 
                                                     low_memory=False, 
                                                     encoding='utf-8',
                                                     on_bad_lines='skip',
                                                     engine='c')):
        total_rows += len(chunk_df)
        
        if first_chunk:
            # Write first chunk (creates file)
            chunk_df.to_parquet(parquet_file, compression='snappy', index=False, engine='pyarrow')
            first_chunk = False
        else:
            # Append: read existing, combine, write back
            existing = pd.read_parquet(parquet_file, engine='pyarrow')
            combined = pd.concat([existing, chunk_df], ignore_index=True)
            combined.to_parquet(parquet_file, compression='snappy', index=False, engine='pyarrow')
            del existing, combined  # Free memory
        
        print(f"  Processed {total_rows:,} rows...", end='\r')
    
    parquet_size = os.path.getsize(parquet_file) / (1024 * 1024)
    ratio = csv_size / parquet_size if parquet_size > 0 else 1
    
    print(f"\n\n✓ Complete!")
    print(f"  Rows: {total_rows:,}")
    print(f"  Output: {parquet_size:.2f} MB ({ratio:.1f}x smaller)")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    if os.path.exists(parquet_file):
        os.remove(parquet_file)

