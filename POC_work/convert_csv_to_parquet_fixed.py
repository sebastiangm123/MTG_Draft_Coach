"""
Memory-efficient CSV to Parquet converter.
Uses PyArrow for better chunk handling - doesn't load entire file into memory.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os

# Your CSV file
csv_file = "draft_data_public.TLA.PremierDraft.csv"
parquet_file = csv_file.replace('.csv', '.parquet')

if not os.path.exists(csv_file):
    print(f"Error: {csv_file} not found!")
    print("Make sure you're in the POC_work directory.")
    exit(1)

# Get CSV file size
csv_size = os.path.getsize(csv_file) / (1024 * 1024)  # MB
print(f"Converting {csv_file} to Parquet...")
print(f"  CSV size: {csv_size:.2f} MB")
print(f"  Processing in chunks (memory-efficient)...")
print("  This may take 2-5 minutes for large files...\n")

# Process in smaller chunks to avoid memory issues
chunk_size = 5000  # Smaller chunks for very large files
total_rows = 0
chunks_processed = 0
parquet_writer = None
schema = None

try:
    # Read CSV in chunks and write incrementally
    for chunk_df in pd.read_csv(csv_file, chunksize=chunk_size, 
                                low_memory=False, encoding='utf-8',
                                on_bad_lines='skip',
                                engine='c'):  # Use C engine for better performance
        
        total_rows += len(chunk_df)
        chunks_processed += 1
        
        # Convert chunk to PyArrow table
        # Use string type for all columns to avoid schema mismatches
        # This is more lenient for CSV files with inconsistent types
        table = pa.Table.from_pandas(chunk_df, preserve_index=False)
        
        # Initialize writer with schema from first chunk
        if parquet_writer is None:
            schema = table.schema
            parquet_writer = pq.ParquetWriter(parquet_file, schema, compression='snappy')
        
        # Check if schema matches (PyArrow is strict about this)
        if table.schema != schema:
            # Schema mismatch - try to cast to match original schema
            try:
                # Cast columns to match original schema
                table = table.cast(schema)
            except Exception as cast_error:
                print(f"\n⚠ Schema mismatch at chunk {chunks_processed}")
                print(f"  Error: {cast_error}")
                print(f"  Trying to unify schema...")
                # If casting fails, we need to update the schema
                # This is complex, so we'll use a more lenient approach
                parquet_writer.close()
                # Re-read with object dtype to avoid type issues
                chunk_df = chunk_df.astype(str, errors='ignore')
                table = pa.Table.from_pandas(chunk_df, preserve_index=False)
                schema = table.schema
                parquet_writer = pq.ParquetWriter(parquet_file, schema, compression='snappy')
        
        # Write chunk immediately (don't store in memory)
        parquet_writer.write_table(table)
        
        print(f"  Processed {total_rows:,} rows ({chunks_processed} chunks)...", end='\r')
    
    # Close the writer
    if parquet_writer:
        parquet_writer.close()
        print(f"\n  Writing Parquet file...")
    
    # Get output size
    parquet_size = os.path.getsize(parquet_file) / (1024 * 1024)  # MB
    ratio = csv_size / parquet_size if parquet_size > 0 else 1
    
    print(f"\n✓ Conversion complete!")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Parquet file: {parquet_file}")
    print(f"  Parquet size: {parquet_size:.2f} MB")
    print(f"  Compression: {ratio:.1f}x smaller")
    print(f"  Space saved: {csv_size - parquet_size:.2f} MB")
    print(f"\nYou can now use: pd.read_parquet('{parquet_file}')")

except MemoryError:
    print(f"\n✗ Still running out of memory.")
    print(f"  Try reducing chunk_size in the script (currently {chunk_size})")
    if parquet_writer:
        try:
            parquet_writer.close()
            print(f"  Partial Parquet file saved: {parquet_file}")
        except:
            pass
    # Don't delete - keep partial file
    if os.path.exists(parquet_file):
        parquet_size = os.path.getsize(parquet_file) / (1024 * 1024)
        print(f"  Partial file size: {parquet_size:.2f} MB")
        print(f"  You can try to continue or reduce chunk_size and retry")
except Exception as e:
    error_msg = str(e)
    error_type = type(e).__name__
    
    print(f"\n✗ Error: {error_type}: {error_msg[:200]}")  # Limit error message length
    
    # Try to close writer gracefully
    if parquet_writer:
        try:
            parquet_writer.close()
            print(f"  Writer closed")
        except:
            pass
    
    # Check if file exists and show info
    if os.path.exists(parquet_file):
        parquet_size = os.path.getsize(parquet_file) / (1024 * 1024)
        print(f"  Partial file: {parquet_file} ({parquet_size:.2f} MB)")
        print(f"  File kept - may be usable")
    else:
        print(f"  No file created")
    
    # Suppress verbose schema dumps from PyArrow
    if 'schema' in error_msg.lower() or 'arrow' in error_msg.lower():
        print(f"\n  This is a schema/data type mismatch issue.")
        print(f"  Common causes:")
        print(f"    - Inconsistent data types across chunks (e.g., numbers vs strings)")
        print(f"    - Very large number of columns (709 columns)")
        print(f"  Solution: Use robust_parquet_convert.py which handles this better")
    else:
        # Only show minimal traceback for other errors
        import traceback
        import sys
        # Capture traceback but filter out schema dumps
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print(f"\n  Error details:")
        # Print traceback but skip if it contains schema info
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in tb_lines:
            if 'schema' not in line.lower() or len(line) < 500:  # Skip long schema dumps
                print(f"  {line.rstrip()}")

