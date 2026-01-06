# How to Convert CSV to Parquet

## Step-by-Step Instructions

### Step 1: Install Dependencies

Make sure you're in the virtual environment, then install:

```bash
# Activate virtual environment first
.\activate.ps1  # or activate.bat

# Install required packages
pip install pandas pyarrow
```

Or install from requirements.txt (which now includes these):
```bash
pip install -r requirements.txt
```

### Step 2: Run the Conversion Script

**Option A: Simple (auto-detects CSV file)**
```bash
cd POC_work
python convert_to_parquet.py
```

**Option B: Specify CSV file**
```bash
python convert_to_parquet.py draft_data_public.TLA.PremierDraft.csv
```

### Step 3: Wait for Conversion

The script will:
- Read your CSV file in chunks (memory efficient)
- Convert to Parquet format
- Show progress and file size reduction
- Create a `.parquet` file next to your CSV

### Step 4: Use the Parquet File

After conversion, you can use the Parquet file:

```python
import pandas as pd

# Read entire file (faster than CSV)
df = pd.read_parquet('draft_data_public.TLA.PremierDraft.parquet')

# Or read only specific columns (MUCH faster!)
df = pd.read_parquet('draft_data_public.TLA.PremierDraft.parquet', 
                    columns=['expansion', 'pick', 'rank'])
```

## What to Expect

- **Time**: 1-3 minutes for a 200MB CSV
- **Output**: A `.parquet` file that's 5-10x smaller
- **Original CSV**: Unchanged (kept as backup)

## Troubleshooting

**Error: "No module named 'pandas'" or "No module named 'pyarrow'"**
- Solution: Install dependencies: `pip install pandas pyarrow`

**Error: "File not found"**
- Solution: Make sure you're in the POC_work directory, or provide full path to CSV

**Error: "Memory error"**
- Solution: The script processes in chunks, but if you have very limited RAM, reduce chunk_size in the script

## Alternative: One-Liner Conversion

If you just want to convert quickly without the script:

```python
import pandas as pd

# Simple conversion
df = pd.read_csv('draft_data_public.TLA.PremierDraft.csv', low_memory=False)
df.to_parquet('draft_data_public.TLA.PremierDraft.parquet', compression='snappy', index=False)
```

But the script is better because it:
- Processes in chunks (more memory efficient)
- Shows progress
- Handles large files better

