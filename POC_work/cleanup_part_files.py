"""
Cleanup script for leftover part files from interrupted conversions.
Also can combine existing part files into a final parquet file.
"""

import os
import glob
import pandas as pd
import sys

def find_part_files(base_name="draft_data_public.TLA.PremierDraft.parquet"):
    """Find all part files matching the pattern."""
    pattern = f"{base_name}.part*"
    part_files = sorted(glob.glob(pattern))
    return part_files

def combine_part_files(part_files, output_file):
    """Combine part files into a single parquet file."""
    if not part_files:
        print("No part files found to combine.")
        return False
    
    print(f"Found {len(part_files)} part files to combine...")
    print(f"Output file: {output_file}\n")
    
    # Combine in batches to avoid memory issues
    batch_size = 20
    combined_dfs = []
    
    for i in range(0, len(part_files), batch_size):
        batch = part_files[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(part_files)-1)//batch_size + 1} ({len(batch)} files)...", end='\r')
        
        batch_dfs = []
        for part_file in batch:
            try:
                df = pd.read_parquet(part_file, engine='pyarrow')
                batch_dfs.append(df)
            except Exception as e:
                print(f"\n  Warning: Could not read {part_file}: {e}")
        
        if batch_dfs:
            batch_combined = pd.concat(batch_dfs, ignore_index=True)
            combined_dfs.append(batch_combined)
            del batch_dfs
    
    # Final combination
    print(f"\nCombining all batches and writing final file...")
    if combined_dfs:
        final_df = pd.concat(combined_dfs, ignore_index=True)
        final_df.to_parquet(output_file, compression='snappy', index=False, engine='pyarrow')
        
        # Get file sizes
        total_size = sum(os.path.getsize(f) for f in part_files) / (1024 * 1024)
        final_size = os.path.getsize(output_file) / (1024 * 1024)
        
        print(f"\n✓ Successfully combined part files!")
        print(f"  Total rows: {len(final_df):,}")
        print(f"  Combined size: {final_size:.2f} MB")
        print(f"  (Part files total: {total_size:.2f} MB)")
        
        # Ask to delete part files
        response = input("\nDelete part files? (y/n): ").strip().lower()
        if response == 'y':
            deleted = 0
            for part_file in part_files:
                try:
                    os.remove(part_file)
                    deleted += 1
                except:
                    pass
            print(f"  Deleted {deleted}/{len(part_files)} part files")
        else:
            print(f"  Part files kept (you can delete them manually)")
        
        return True
    
    return False

def cleanup_part_files(base_name="draft_data_public.TLA.PremierDraft.parquet"):
    """Clean up part files without combining."""
    part_files = find_part_files(base_name)
    
    if not part_files:
        print("No part files found.")
        return
    
    print(f"Found {len(part_files)} part files:")
    for f in part_files[:10]:  # Show first 10
        size = os.path.getsize(f) / (1024 * 1024)
        print(f"  {f} ({size:.2f} MB)")
    if len(part_files) > 10:
        print(f"  ... and {len(part_files) - 10} more")
    
    response = input(f"\nDelete all {len(part_files)} part files? (y/n): ").strip().lower()
    if response == 'y':
        deleted = 0
        for part_file in part_files:
            try:
                os.remove(part_file)
                deleted += 1
            except Exception as e:
                print(f"  Could not delete {part_file}: {e}")
        print(f"  Deleted {deleted}/{len(part_files)} part files")
    else:
        print("  Part files kept")

if __name__ == "__main__":
    base_name = "draft_data_public.TLA.PremierDraft.parquet"
    output_file = base_name
    
    part_files = find_part_files(base_name)
    
    if not part_files:
        print("No part files found.")
        sys.exit(0)
    
    print(f"Found {len(part_files)} part files from interrupted conversion.")
    print("\nOptions:")
    print("  1. Combine part files into final parquet file")
    print("  2. Delete part files (cleanup only)")
    print("  3. Exit")
    
    choice = input("\nChoose option (1/2/3): ").strip()
    
    if choice == "1":
        combine_part_files(part_files, output_file)
    elif choice == "2":
        cleanup_part_files(base_name)
    else:
        print("Exiting...")

