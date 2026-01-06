"""
Quick CSV to Parquet converter (Memory-Efficient Version).
Processes large CSV files in chunks to avoid memory issues.
"""

import pandas as pd
import os

# Your CSV file
csv_file = "draft_data_public.TLA.PremierDraft.csv"
parquet_file = csv_file.replace('.csv', '.parquet')

#probability of a 

if not os.path.exists(csv_file):
    print(f"Error: {csv_file} not found!")
    print("Make sure you're in the POC_work directory.")
    exit(1)

# Get CSV file size
csv_size = os.path.getsize(csv_file) / (1024 * 1024)  # MB
print(f"Converting {csv_file} to Parquet...")
print(f"  CSV size: {csv_size:.2f} MB")
print(f"  Processing in chunks to avoid memory issues...")
print("  This may take 2-5 minutes for large files...\n")

# Process in chunks (50,000 rows at a time - adjust if needed)
chunk_size = 50000
first_chunk = True
total_rows = 0
chunks_processed = 0

try:
    # Read CSV in chunks
    for chunk_df in pd.read_csv(csv_file, chunksize=chunk_size, 
                                low_memory=False, encoding='utf-8',
                                on_bad_lines='skip'):
        total_rows += len(chunk_df)
        chunks_processed += 1
        
        # Write first chunk (creates the file)
        if first_chunk:
            chunk_df.to_parquet(parquet_file, compression='snappy', index=False)
            first_chunk = False
            print(f"  Created Parquet file...")
        else:
            # Append subsequent chunks
            # Read existing data
            existing_df = pd.read_parquet(parquet_file)
            # Combine with new chunk
            combined_df = pd.concat([existing_df, chunk_df], ignore_index=True)
            # Write back (this is the trade-off - we rewrite the file each time)
            combined_df.to_parquet(parquet_file, compression='snappy', index=False)
        
        print(f"  Processed {total_rows:,} rows ({chunks_processed} chunks)...", end='\r')
    
    # Get output size
    parquet_size = os.path.getsize(parquet_file) / (1024 * 1024)  # MB
    ratio = csv_size / parquet_size if parquet_size > 0 else 1
    
    print(f"\n\n✓ Conversion complete!")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Parquet file: {parquet_file}")
    print(f"  Parquet size: {parquet_size:.2f} MB")
    print(f"  Compression: {ratio:.1f}x smaller")
    print(f"  Space saved: {csv_size - parquet_size:.2f} MB")
    print(f"\nYou can now use: pd.read_parquet('{parquet_file}')")

except MemoryError:
    print(f"\n✗ Still running out of memory. Try reducing chunk_size.")
    print(f"  Edit quick_convert.py and change chunk_size to 10000 or 5000")
    if os.path.exists(parquet_file):
        os.remove(parquet_file)
except Exception as e:
    print(f"\n✗ Error: {e}")
    if os.path.exists(parquet_file):
        os.remove(parquet_file)

