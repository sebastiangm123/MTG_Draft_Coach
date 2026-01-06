"""
Simple script to convert CSV to Parquet format.
Run this once to convert your draft data CSV to Parquet.
"""

import pandas as pd
import os
import sys
from pathlib import Path


def convert_csv_to_parquet(csv_file: str, parquet_file: str = None, 
                          chunk_size: int = 100000, compression: str = 'snappy'):
    """
    Convert CSV file to Parquet format.
    
    Args:
        csv_file: Path to input CSV file
        parquet_file: Path to output Parquet file (optional, auto-generated if not provided)
        chunk_size: Number of rows to process per chunk (for memory efficiency)
        compression: Compression codec ('snappy', 'gzip', 'brotli', 'zstd')
    
    Returns:
        Path to created Parquet file
    """
    # Check if CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found: {csv_file}")
        return None
    
    # Generate output filename if not provided
    if parquet_file is None:
        parquet_file = csv_file.replace('.csv', '.parquet')
        # Handle case where .csv might be uppercase
        if parquet_file == csv_file:
            parquet_file = csv_file.replace('.CSV', '.parquet')
    
    # Get file sizes
    csv_size_mb = os.path.getsize(csv_file) / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"Converting CSV to Parquet")
    print(f"{'='*60}")
    print(f"Input file:  {csv_file}")
    print(f"Output file: {parquet_file}")
    print(f"Input size:  {csv_size_mb:.2f} MB")
    print(f"Compression: {compression}")
    print(f"{'='*60}\n")
    
    # Read CSV in chunks and write to Parquet
    print("Reading CSV file...")
    first_chunk = True
    total_rows = 0
    chunks_processed = 0
    
    try:
        # Use pandas to read CSV in chunks
        for chunk_df in pd.read_csv(csv_file, chunksize=chunk_size, 
                                   low_memory=False, encoding='utf-8',
                                   on_bad_lines='skip'):  # Skip bad lines instead of failing
            
            total_rows += len(chunk_df)
            chunks_processed += 1
            
            # Write first chunk (creates file)
            if first_chunk:
                chunk_df.to_parquet(parquet_file, compression=compression, index=False)
                first_chunk = False
                print(f"  Created Parquet file...")
            else:
                # Append to existing file
                # Read existing data
                existing_df = pd.read_parquet(parquet_file)
                # Combine with new chunk
                combined_df = pd.concat([existing_df, chunk_df], ignore_index=True)
                # Write back
                combined_df.to_parquet(parquet_file, compression=compression, index=False)
            
            print(f"  Processed {total_rows:,} rows ({chunks_processed} chunks)...", end='\r')
        
        # Get output file size
        parquet_size_mb = os.path.getsize(parquet_file) / (1024 * 1024)
        compression_ratio = csv_size_mb / parquet_size_mb if parquet_size_mb > 0 else 1
        
        print(f"\n\n{'='*60}")
        print(f"✓ Conversion Complete!")
        print(f"{'='*60}")
        print(f"Total rows:        {total_rows:,}")
        print(f"Output size:       {parquet_size_mb:.2f} MB")
        print(f"Compression ratio: {compression_ratio:.1f}x smaller")
        print(f"Space saved:       {csv_size_mb - parquet_size_mb:.2f} MB")
        print(f"{'='*60}\n")
        
        return parquet_file
    
    except Exception as e:
        print(f"\n✗ Error during conversion: {e}")
        if os.path.exists(parquet_file):
            print(f"  Removing incomplete file: {parquet_file}")
            os.remove(parquet_file)
        raise


def main():
    """Main function with command-line interface."""
    # Default CSV file name
    default_csv = "draft_data_public.TLA.PremierDraft.csv"
    
    # Check if CSV file exists in current directory
    if os.path.exists(default_csv):
        csv_file = default_csv
        print(f"Found CSV file: {csv_file}")
    else:
        # Try to find any CSV file in current directory
        csv_files = list(Path('.').glob('*.csv'))
        if csv_files:
            csv_file = str(csv_files[0])
            print(f"Found CSV file: {csv_file}")
        else:
            print("No CSV file found in current directory.")
            print(f"Looking for: {default_csv}")
            print("\nUsage:")
            print("  python convert_to_parquet.py")
            print("  OR")
            print("  python convert_to_parquet.py <path_to_csv_file>")
            sys.exit(1)
    
    # Convert
    parquet_file = convert_csv_to_parquet(csv_file)
    
    if parquet_file:
        print(f"\nYou can now use the Parquet file for faster queries:")
        print(f"  import pandas as pd")
        print(f"  df = pd.read_parquet('{parquet_file}')")
        print(f"  # Or read only specific columns:")
        print(f"  df = pd.read_parquet('{parquet_file}', columns=['expansion', 'pick', 'rank'])")
        print(f"\nOriginal CSV file is unchanged and can be kept as backup.")


if __name__ == "__main__":
    # Allow CSV file to be passed as command-line argument
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
        if not os.path.exists(csv_file):
            print(f"Error: File not found: {csv_file}")
            sys.exit(1)
        convert_csv_to_parquet(csv_file)
    else:
        main()

