"""
Parquet File Explorer
Safely explores parquet files without loading entire file into memory.
Shows schema, statistics, and sample rows.

Usage:
    python explore_parquet.py <parquet_file> [num_rows] [num_columns]
    
Examples:
    python explore_parquet.py data.parquet
    python explore_parquet.py data.parquet 20 30
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import os
import sys
from pathlib import Path

# Try to import rich for pretty printing, fallback to basic if not available
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def print_section(title: str, console=None):
    """Print a section header."""
    if HAS_RICH and console:
        console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
        console.print(f"[bold cyan]{title}[/bold cyan]")
        console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")
    else:
        print(f"\n{'='*80}")
        print(f"{title}")
        print(f"{'='*80}\n")


def explore_parquet(parquet_file: str, num_rows: int = 10, num_columns: int = 20):
    """
    Explore a parquet file safely.
    
    Args:
        parquet_file: Path to parquet file
        num_rows: Number of sample rows to show
        num_columns: Maximum number of columns to show details for
    """
    if not os.path.exists(parquet_file):
        print(f"❌ Error: File not found: {parquet_file}")
        return
    
    # Initialize console if rich is available
    console = Console() if HAS_RICH else None
    
    # Get file size
    file_size = os.path.getsize(parquet_file) / (1024 * 1024)  # MB
    
    # Print header
    if HAS_RICH and console:
        console.print(Panel.fit(
            f"[bold green]Exploring Parquet File[/bold green]\n"
            f"[yellow]File:[/yellow] {parquet_file}\n"
            f"[yellow]Size:[/yellow] {file_size:.2f} MB",
            title="Parquet Explorer",
            border_style="green"
        ))
    else:
        print(f"\n{'='*80}")
        print(f"📊 Exploring Parquet File: {parquet_file}")
        print(f"{'='*80}")
        print(f"📁 File size: {file_size:.2f} MB\n")
    
    try:
        # Use PyArrow to read metadata without loading data
        parquet_file_obj = pq.ParquetFile(parquet_file)
        metadata = parquet_file_obj.metadata
        
        # Basic file info
        print_section("📋 File Information", console)
        
        if HAS_RICH and console:
            info_table = Table(show_header=False, box=box.SIMPLE)
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="yellow")
            info_table.add_row("Total rows", f"{metadata.num_rows:,}")
            info_table.add_row("Total columns", f"{len(metadata.schema)}")
            info_table.add_row("Row groups", f"{metadata.num_row_groups}")
            compression = metadata.row_group(0).column(0).compression if metadata.num_row_groups > 0 else 'N/A'
            info_table.add_row("Compression", compression)
            console.print(info_table)
        else:
            print(f"  📊 Total rows:     {metadata.num_rows:,}")
            print(f"  📊 Total columns:  {len(metadata.schema)}")
            print(f"  📊 Row groups:     {metadata.num_row_groups}")
            compression = metadata.row_group(0).column(0).compression if metadata.num_row_groups > 0 else 'N/A'
            print(f"  📊 Compression:    {compression}")
        
        # Schema information
        print_section("📐 Schema Information", console)
        
        # Use Arrow schema which has proper field information
        arrow_schema = parquet_file_obj.schema_arrow
        column_info = []
        
        for i, field in enumerate(arrow_schema):
            col_name = field.name
            col_type = str(field.type)
            nullable = "nullable" if field.nullable else "required"
            
            column_info.append({
                'index': i,
                'name': col_name,
                'type': col_type,
                'nullable': nullable
            })
        
        if HAS_RICH and console:
            console.print(f"[yellow]Total columns:[/yellow] {len(column_info)}\n")
        else:
            print(f"  📊 Total columns: {len(column_info)}\n")
        
        # Show first N columns in detail
        show_columns = min(num_columns, len(column_info))
        
        if HAS_RICH and console:
            schema_table = Table(title=f"First {show_columns} Columns (showing details)", box=box.ROUNDED)
            schema_table.add_column("Index", style="cyan", width=8)
            schema_table.add_column("Column Name", style="green", width=40)
            schema_table.add_column("Type", style="yellow", width=25)
            schema_table.add_column("Nullable", style="magenta", width=10)
            
            for col in column_info[:show_columns]:
                col_name = col['name'][:38] + '..' if len(col['name']) > 40 else col['name']
                schema_table.add_row(
                    str(col['index']),
                    col_name,
                    col['type'],
                    col['nullable']
                )
            console.print(schema_table)
        else:
            print(f"  First {show_columns} columns (showing details):")
            print(f"  {'-'*85}")
            print(f"  {'Index':<8} {'Column Name':<45} {'Type':<25} {'Nullable'}")
            print(f"  {'-'*85}")
            
            for col in column_info[:show_columns]:
                col_name = col['name'][:43] + '..' if len(col['name']) > 45 else col['name']
                print(f"  {col['index']:<8} {col_name:<45} {col['type']:<25} {col['nullable']}")
        
        if len(column_info) > show_columns:
            if HAS_RICH and console:
                console.print(f"\n[yellow]... and {len(column_info) - show_columns} more columns[/yellow]")
                console.print(f"\n[cyan]All column names:[/cyan]")
            else:
                print(f"\n  ... and {len(column_info) - show_columns} more columns")
                print(f"\n  All column names:")
            
            for i in range(show_columns, len(column_info), 10):
                batch = column_info[i:min(i+10, len(column_info))]
                names = [col['name'] for col in batch]
                if HAS_RICH and console:
                    console.print(f"  [dim]{', '.join(names)}[/dim]")
                else:
                    print(f"  {', '.join(names)}")
        
        # Read sample rows (only load what we need)
        print_section(f"📊 Sample Data (first {num_rows} rows, first {show_columns} columns)", console)
        
        # Read only the columns we want to display
        columns_to_read = [col['name'] for col in column_info[:show_columns]]
        
        # Read sample rows using pandas (it handles this efficiently)
        try:
            df_sample = pd.read_parquet(
                parquet_file, 
                columns=columns_to_read,
                engine='pyarrow'
            )
            
            # Show only first N rows
            df_display = df_sample.head(num_rows)
            
            # Display with pandas (it will truncate if too wide)
            pd.set_option('display.max_columns', show_columns)
            pd.set_option('display.width', 120)
            pd.set_option('display.max_colwidth', 30)
            
            if HAS_RICH and console:
                # Convert to rich table for better formatting
                data_table = Table(title="Sample Data", box=box.ROUNDED, show_lines=True)
                for col in df_display.columns:
                    data_table.add_column(col[:30], overflow="fold", width=15)
                
                for idx, row in df_display.iterrows():
                    data_table.add_row(*[str(val)[:30] if pd.notna(val) else "NaN" for val in row])
                
                console.print(data_table)
            else:
                print(df_display.to_string())
            
            if len(df_sample) > num_rows:
                if HAS_RICH and console:
                    console.print(f"\n[yellow]... and {len(df_sample) - num_rows:,} more rows[/yellow]")
                else:
                    print(f"\n  ... and {len(df_sample) - num_rows:,} more rows")
            
            # Export to CSV (all columns, top 100 rows)
            export_rows = 100  # Always export top 100 rows
            csv_export_file = parquet_file.replace('.parquet', '_sample.csv')
            
            # Read all columns for export (not just displayed ones)
            try:
                # Use PyArrow to read only what we need (more memory efficient)
                parquet_file_obj = pq.ParquetFile(parquet_file)
                # Read first 100 rows using iter_batches
                batches = []
                rows_collected = 0
                for batch in parquet_file_obj.iter_batches():
                    batches.append(batch)
                    rows_collected += len(batch)
                    if rows_collected >= export_rows:
                        break
                
                if batches:
                    # Combine batches and convert to pandas
                    table = pa.Table.from_batches(batches)
                    df_export = table.to_pandas().head(export_rows)
                    df_export.to_csv(csv_export_file, index=False)
                else:
                    # Fallback: read normally and use head
                    df_export_full = pd.read_parquet(parquet_file, engine='pyarrow')
                    df_export = df_export_full.head(export_rows)
                    df_export.to_csv(csv_export_file, index=False)
                    del df_export_full
                
                csv_size = os.path.getsize(csv_export_file) / (1024 * 1024)  # MB
                
                if HAS_RICH and console:
                    console.print(f"\n[bold green]✓ Exported top {len(df_export)} rows (all {len(df_export.columns)} columns) to:[/bold green]")
                    console.print(f"[cyan]  {csv_export_file}[/cyan]")
                    console.print(f"[dim]  File size: {csv_size:.2f} MB[/dim]")
                else:
                    print(f"\n✓ Exported top {len(df_export)} rows (all {len(df_export.columns)} columns) to: {csv_export_file}")
                    print(f"  File size: {csv_size:.2f} MB")
            except Exception as e:
                # Fallback: export just the displayed columns
                if HAS_RICH and console:
                    console.print(f"\n[yellow]⚠ Error exporting all columns: {e}[/yellow]")
                    console.print(f"[yellow]  Falling back to displayed columns only...[/yellow]")
                else:
                    print(f"\n⚠ Error exporting all columns: {e}")
                    print(f"  Falling back to displayed columns only...")
                
                # Try to read all columns with a simpler approach
                try:
                    df_export_full = pd.read_parquet(parquet_file, engine='pyarrow')
                    df_export = df_export_full.head(export_rows)
                    df_export.to_csv(csv_export_file, index=False)
                    del df_export_full
                    
                    csv_size = os.path.getsize(csv_export_file) / (1024 * 1024)
                    if HAS_RICH and console:
                        console.print(f"[bold green]✓ Exported top {len(df_export)} rows (all {len(df_export.columns)} columns) to:[/bold green]")
                        console.print(f"[cyan]  {csv_export_file}[/cyan]")
                        console.print(f"[dim]  File size: {csv_size:.2f} MB[/dim]")
                    else:
                        print(f"✓ Exported top {len(df_export)} rows (all {len(df_export.columns)} columns) to: {csv_export_file}")
                        print(f"  File size: {csv_size:.2f} MB")
                except Exception as e2:
                    # Last resort: export just displayed columns
                    df_display.to_csv(csv_export_file, index=False)
                    if HAS_RICH and console:
                        console.print(f"[yellow]⚠ Exported {len(df_display)} rows ({len(df_display.columns)} columns) to:[/yellow]")
                        console.print(f"[cyan]  {csv_export_file}[/cyan]")
                        console.print(f"[dim]  (Note: Only displayed columns exported due to error)[/dim]")
                    else:
                        print(f"⚠ Exported {len(df_display)} rows ({len(df_display.columns)} columns) to: {csv_export_file}")
                        print(f"  (Note: Only displayed columns exported due to error)")
            
            # Basic statistics for numeric columns
            print_section("📈 Basic Statistics (numeric columns only)", console)
            
            numeric_cols = df_sample.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                stats = df_sample[numeric_cols].describe()
                if HAS_RICH and console:
                    console.print(stats.to_string())
                else:
                    print(stats.to_string())
            else:
                if HAS_RICH and console:
                    console.print("[yellow]  No numeric columns found in sample[/yellow]")
                else:
                    print("  ⚠ No numeric columns found in sample")
            
        except MemoryError:
            if HAS_RICH and console:
                console.print("[red]  ⚠ Cannot load sample data - file too large[/red]")
                console.print("[yellow]  Schema information shown above[/yellow]")
            else:
                print("  ⚠ Cannot load sample data - file too large")
                print("  Schema information shown above")
        except Exception as e:
            if HAS_RICH and console:
                console.print(f"[red]  ⚠ Could not load sample data: {e}[/red]")
                console.print("[yellow]  Schema information shown above[/yellow]")
            else:
                print(f"  ⚠ Could not load sample data: {e}")
                print("  Schema information shown above")
        
        # Column statistics (if file is not too large)
        print_section("📊 Column Summary", console)
        
        try:
            # Try to get some statistics without loading everything
            # Read just a small sample for statistics (first 10,000 rows)
            # Use PyArrow iter_batches for memory efficiency
            parquet_file_obj = pq.ParquetFile(parquet_file)
            batches = []
            rows_collected = 0
            for batch in parquet_file_obj.iter_batches(max_rows=10000):
                batches.append(batch)
                rows_collected += len(batch)
                if rows_collected >= 10000:
                    break
            
            if batches:
                table = pa.Table.from_batches(batches)
                df_stats = table.to_pandas().head(10000)
            else:
                # Fallback
                df_stats_full = pd.read_parquet(parquet_file, engine='pyarrow')
                df_stats = df_stats_full.head(10000)
                del df_stats_full
            
            print(f"\nData types summary:")
            dtype_counts = df_stats.dtypes.value_counts()
            for dtype, count in dtype_counts.items():
                print(f"  {dtype}: {count} columns")
            
            print(f"\nNull value counts (in first 10,000 rows):")
            null_counts = df_stats.isnull().sum()
            null_cols = null_counts[null_counts > 0].head(20)
            if len(null_cols) > 0:
                for col, count in null_cols.items():
                    pct = (count / len(df_stats)) * 100
                    print(f"  {col}: {count:,} ({pct:.1f}%)")
            else:
                print("  No null values found in sample")
            
            if len(null_counts) > 20:
                print(f"  ... and {len(null_counts) - 20} more columns checked")
                
        except Exception as e:
            print(f"  Could not compute statistics: {e}")
        
        if HAS_RICH and console:
            console.print(Panel.fit(
                "[bold green]✓ Exploration Complete![/bold green]",
                border_style="green"
            ))
        else:
            print(f"\n{'='*80}")
            print(f"✓ Exploration complete!")
            print(f"{'='*80}\n")
        
    except Exception as e:
        if HAS_RICH and console:
            console.print(f"\n[bold red]✗ Error reading parquet file: {e}[/bold red]")
        else:
            print(f"\n✗ Error reading parquet file: {e}")
        import traceback
        print("\nFull error:")
        traceback.print_exc()


def main():
    """Main function with command-line interface."""
    console = Console() if HAS_RICH else None
    
    if len(sys.argv) < 2:
        if HAS_RICH and console:
            console.print("[bold red]❌ Error: No parquet file specified![/bold red]\n")
            console.print("[yellow]Usage:[/yellow]")
            console.print("  [cyan]python explore_parquet.py <path_to_parquet_file> [num_rows] [num_columns][/cyan]")
            console.print("\n[yellow]Examples:[/yellow]")
            console.print("  [cyan]python explore_parquet.py data.parquet[/cyan]")
            console.print("  [cyan]python explore_parquet.py data.parquet 20 30[/cyan]")
        else:
            print("❌ Error: No parquet file specified!")
            print("\nUsage:")
            print("  python explore_parquet.py <path_to_parquet_file> [num_rows] [num_columns]")
            print("\nExamples:")
            print("  python explore_parquet.py data.parquet")
            print("  python explore_parquet.py data.parquet 20 30")
        sys.exit(1)
    
    parquet_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(parquet_file):
        if HAS_RICH and console:
            console.print(f"[bold red]❌ Error: File not found: {parquet_file}[/bold red]")
        else:
            print(f"❌ Error: File not found: {parquet_file}")
        sys.exit(1)
    
    # Optional: specify number of rows/columns to show
    num_rows = 10
    num_columns = 20
    
    if len(sys.argv) > 2:
        try:
            num_rows = int(sys.argv[2])
        except:
            pass
    
    if len(sys.argv) > 3:
        try:
            num_columns = int(sys.argv[3])
        except:
            pass
    
    explore_parquet(parquet_file, num_rows=num_rows, num_columns=num_columns)


if __name__ == "__main__":
    main()

