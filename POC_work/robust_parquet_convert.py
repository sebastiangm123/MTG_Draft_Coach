"""
Robust CSV to Parquet converter with better error handling.
Uses pandas' built-in to_parquet which is more reliable.
"""

import pandas as pd
import os
import sys

csv_file = "draft_data_public.TLA.PremierDraft.csv"
parquet_file = csv_file.replace('.csv', '.parquet')

if not os.path.exists(csv_file):
    print(f"Error: {csv_file} not found!")
    print("Make sure you're in the POC_work directory.")
    sys.exit(1)

csv_size = os.path.getsize(csv_file) / (1024 * 1024)
print(f"Converting {csv_file} to Parquet...")
print(f"  CSV size: {csv_size:.2f} MB")
print(f"  Processing in chunks (chunk_size=5000)...")
print("  This may take 3-5 minutes for large files...\n")

chunk_size = 5000
total_rows = 0
chunks_processed = 0
first_chunk = True
temp_files = []

try:
    for chunk_num, chunk_df in enumerate(pd.read_csv(csv_file, 
                                                     chunksize=chunk_size, 
                                                     low_memory=False, 
                                                     encoding='utf-8',
                                                     on_bad_lines='skip',
                                                     engine='c')):
        total_rows += len(chunk_df)
        chunks_processed += 1
        
        # Write each chunk to a temporary parquet file
        temp_file = f"{parquet_file}.part{chunk_num}"
        chunk_df.to_parquet(temp_file, compression='snappy', index=False, engine='pyarrow')
        temp_files.append(temp_file)
        
        print(f"  Processed {total_rows:,} rows ({chunks_processed} chunks)...", end='\r')
        
        # Free memory
        del chunk_df
    
    # Combine all temporary files
    print(f"\n  Combining {len(temp_files)} chunks into final file...")
    print(f"  This may take a few minutes...")
    
    # Read all temp files and combine (in batches to avoid memory issues)
    batch_size = 20  # Combine 20 files at a time
    combined_dfs = []
    
    for i in range(0, len(temp_files), batch_size):
        batch = temp_files[i:i+batch_size]
        print(f"  Combining batch {i//batch_size + 1}/{(len(temp_files)-1)//batch_size + 1} ({len(batch)} files)...", end='\r')
        
        batch_dfs = []
        for temp_file in batch:
            if os.path.exists(temp_file):
                df = pd.read_parquet(temp_file, engine='pyarrow')
                batch_dfs.append(df)
                os.remove(temp_file)  # Clean up temp file immediately
        
        if batch_dfs:
            batch_combined = pd.concat(batch_dfs, ignore_index=True)
            combined_dfs.append(batch_combined)
            del batch_dfs  # Free memory
    
    # Final combination
    print(f"\n  Writing final combined file...")
    if combined_dfs:
        final_df = pd.concat(combined_dfs, ignore_index=True)
        final_df.to_parquet(parquet_file, compression='snappy', index=False, engine='pyarrow')
        del final_df, combined_dfs  # Free memory
    
    # Get output size
    parquet_size = os.path.getsize(parquet_file) / (1024 * 1024)
    ratio = csv_size / parquet_size if parquet_size > 0 else 1
    
    print(f"\n✓ Conversion complete!")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Parquet file: {parquet_file}")
    print(f"  Parquet size: {parquet_size:.2f} MB")
    print(f"  Compression: {ratio:.1f}x smaller")
    print(f"  Space saved: {csv_size - parquet_size:.2f} MB")
    print(f"\nYou can now use: pd.read_parquet('{parquet_file}')")

except KeyboardInterrupt:
    print(f"\n\n⚠ Conversion interrupted by user")
    print(f"  Processed {total_rows:,} rows before interruption")
    # Clean up temp files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    if os.path.exists(parquet_file):
        print(f"  Note: {parquet_file} may be incomplete")
    sys.exit(1)

except MemoryError:
    print(f"\n✗ Out of memory error")
    print(f"  Processed {total_rows:,} rows before error")
    print(f"  Try reducing chunk_size (currently {chunk_size})")
    # Clean up temp files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    if os.path.exists(parquet_file):
        print(f"  Note: {parquet_file} may be incomplete")
    sys.exit(1)

except Exception as e:
    print(f"\n✗ Error: {type(e).__name__}: {e}")
    print(f"  Processed {total_rows:,} rows before error")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
    
    # Clean up temp files
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
    
    # Don't delete the parquet file - it might be partially complete
    if os.path.exists(parquet_file):
        parquet_size = os.path.getsize(parquet_file) / (1024 * 1024)
        print(f"\n  Partial file exists: {parquet_file} ({parquet_size:.2f} MB)")
        print(f"  File kept - check if it's usable or delete manually")
    
    sys.exit(1)

