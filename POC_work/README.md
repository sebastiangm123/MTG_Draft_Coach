# MTG Draft Coach - POC Components

This folder contains three proof-of-concept components for the MTG Draft Coach project.

## Components

### 1. 17Lands Draft Data Processor (`17lands_scraper.py`)

Processes 17Lands draft data CSV files and creates a SQLite database for efficient querying.

**Usage:**

```python
from 17lands_scraper import DraftDataProcessor

# Initialize processor
processor = DraftDataProcessor("draft_data.db")

# Process CSV file (processes in chunks for large files)
processor.process_csv_file("draft_data_public.TLA.PremierDraft.csv", 
                          chunk_size=10000, 
                          max_rows=None)  # None = process all rows

# Update aggregated card statistics
processor.update_card_statistics()

# Query card details
card_details = processor.get_card_details("Sokka's Haiku")
print(card_details)

# Search for cards
results = processor.search_cards("Sokka", limit=10)
for card in results:
    print(f"{card['card_name']}: {card.get('win_rate', 0):.2%} win rate")

# Get all picks from a specific draft
draft_picks = processor.get_draft_picks("draft_id_here")

# Close connection when done
processor.close()
```

**Database Schema:**
- `draft_picks`: Individual draft pick records
- `card_stats`: Aggregated card statistics (win rates, pick positions, etc.)

**Note:** The processor handles large CSV files efficiently by processing in chunks. The database file will be created in the current directory.

### 2. OpenAI Chat (`openai_chat.py`)

Simple programmatic interface for chatting with OpenAI.

**Setup:**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Usage:**
```python
from openai_chat import OpenAIChat

chat = OpenAIChat(model="gpt-4")
response = chat.chat("What makes a good first pick in a draft?")
print(response)

# With system prompt
chat.set_system_prompt("You are an expert MTG draft coach.")
response = chat.chat("Should I pick Lightning Bolt or Counterspell?")
```

### 3. MTG Arena Log Reader (`mtga_log_reader.py`)

Reads and parses MTG Arena logs in real-time to understand game events.

**Prerequisites:**
1. Open MTG Arena
2. Click the gear icon
3. Go to "View Account"
4. Check "Detailed Logs"
5. Restart MTG Arena

**Usage:**
```python
from mtga_log_reader import MTGALogReader

reader = MTGALogReader()

# Register callback for draft picks
def on_draft_pick(event):
    print(f"Draft pick detected: {event}")

reader.register_callback('draft_pick', on_draft_pick)

# Start real-time monitoring
reader.start_monitoring(interval=0.5)

# Or read recent events
recent_events = reader.get_recent_events(100)
```

## Installation

### Setup Virtual Environment

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment:**
   
   **Windows PowerShell:**
   ```powershell
   .\activate.ps1
   ```
   Or manually:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   
   **Windows Command Prompt:**
   ```cmd
   activate.bat
   ```
   Or manually:
   ```cmd
   venv\Scripts\activate.bat
   ```
   
   **Linux/Mac:**
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Deactivate when done:**
   ```bash
   deactivate
   ```

## Notes

- The draft data processor creates a SQLite database (`draft_data.db`) from CSV files
- Large CSV files are processed in chunks to manage memory efficiently
- The log reader uses the default Windows log location. Adjust `log_path` if needed
- All components are designed to be modular and can be integrated together

