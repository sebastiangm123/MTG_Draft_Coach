"""
MTG Arena Log Reader
Reads and parses MTG Arena logs in real-time to understand game events.
"""

import os
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime


class MTGALogReader:
    """Reads and parses MTG Arena log files in real-time."""
    
    # Default log location on Windows
    DEFAULT_LOG_PATH = Path(os.path.expanduser("~")) / "AppData" / "LocalLow" / "Wizards Of The Coast" / "MTGA" / "Player.log"
    
    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize log reader.
        
        Args:
            log_path: Path to MTG Arena log file. If None, uses default Windows location.
        """
        self.log_path = log_path or self.DEFAULT_LOG_PATH
        self.last_position = 0
        self.running = False
        
        # Event patterns for common MTG Arena log events
        self.event_patterns = {
            'draft_pick': re.compile(r'DraftPick.*?cardId.*?(\d+)'),
            'match_start': re.compile(r'Match.*?started|Game.*?started'),
            'match_end': re.compile(r'Match.*?completed|Game.*?completed'),
            'card_played': re.compile(r'Card.*?played|PlayCard'),
            'life_total': re.compile(r'lifeTotal.*?(\d+)'),
            'zone_change': re.compile(r'zone.*?change|ZoneChange'),
            'deck_submit': re.compile(r'Deck.*?submitted|SubmitDeck'),
        }
        
        # Callbacks for different event types
        self.event_callbacks: Dict[str, List[Callable]] = {}
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        Register a callback function for a specific event type.
        
        Args:
            event_type: Type of event ('draft_pick', 'match_start', etc.)
            callback: Function to call when event is detected
        """
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        self.event_callbacks[event_type].append(callback)
    
    def _parse_log_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single log line and extract relevant information.
        
        Args:
            line: Log line to parse
        
        Returns:
            Dictionary with event information or None if no match
        """
        # Check for timestamp
        timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.*?)\]', line)
        timestamp = timestamp_match.group(1) if timestamp_match else None
        
        # Check each event pattern
        for event_type, pattern in self.event_patterns.items():
            match = pattern.search(line)
            if match:
                event_data = {
                    'type': event_type,
                    'timestamp': timestamp,
                    'raw_line': line.strip(),
                    'match': match.group(0) if match else None
                }
                
                # Extract specific data based on event type
                if event_type == 'draft_pick':
                    card_id_match = re.search(r'cardId.*?(\d+)', line)
                    if card_id_match:
                        event_data['card_id'] = card_id_match.group(1)
                
                elif event_type == 'life_total':
                    life_match = re.search(r'lifeTotal.*?(\d+)', line)
                    if life_match:
                        event_data['life_total'] = int(life_match.group(1))
                
                return event_data
        
        return None
    
    def _trigger_callbacks(self, event_data: Dict):
        """Trigger registered callbacks for an event."""
        event_type = event_data.get('type')
        if event_type and event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    callback(event_data)
                except Exception as e:
                    print(f"Error in callback for {event_type}: {e}")
    
    def read_new_lines(self) -> List[Dict]:
        """
        Read new lines from the log file since last read.
        
        Returns:
            List of parsed event dictionaries
        """
        events = []
        
        if not self.log_path.exists():
            return events
        
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Seek to last position
                f.seek(self.last_position)
                
                # Read new lines
                new_lines = f.readlines()
                self.last_position = f.tell()
                
                # Parse each line
                for line in new_lines:
                    event = self._parse_log_line(line)
                    if event:
                        events.append(event)
                        self._trigger_callbacks(event)
        
        except Exception as e:
            print(f"Error reading log file: {e}")
        
        return events
    
    def start_monitoring(self, interval: float = 0.5, callback: Optional[Callable] = None):
        """
        Start monitoring the log file in real-time.
        
        Args:
            interval: Time in seconds between checks
            callback: Optional callback function called with all new events
        """
        self.running = True
        print(f"Starting to monitor MTG Arena log: {self.log_path}")
        print("Press Ctrl+C to stop...")
        
        try:
            while self.running:
                events = self.read_new_lines()
                
                if events:
                    if callback:
                        callback(events)
                    else:
                        # Default: print events
                        for event in events:
                            print(f"[{event.get('timestamp', 'N/A')}] {event['type']}: {event.get('raw_line', '')[:100]}")
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\nStopping log monitoring...")
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop monitoring the log file."""
        self.running = False
    
    def get_recent_events(self, num_lines: int = 100) -> List[Dict]:
        """
        Get recent events from the log file.
        
        Args:
            num_lines: Number of recent lines to read
        
        Returns:
            List of parsed events
        """
        events = []
        
        if not self.log_path.exists():
            return events
        
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last N lines
                lines = f.readlines()[-num_lines:]
                
                for line in lines:
                    event = self._parse_log_line(line)
                    if event:
                        events.append(event)
        
        except Exception as e:
            print(f"Error reading log file: {e}")
        
        return events


def example_callback(event_data: Dict):
    """Example callback function for log events."""
    print(f"Event detected: {event_data['type']}")
    if 'card_id' in event_data:
        print(f"  Card ID: {event_data['card_id']}")


def main():
    """Example usage of the log reader."""
    reader = MTGALogReader()
    
    # Check if log file exists
    if not reader.log_path.exists():
        print(f"Log file not found at: {reader.log_path}")
        print("\nTo enable MTG Arena logging:")
        print("1. Open MTG Arena")
        print("2. Click the gear icon")
        print("3. Go to 'View Account'")
        print("4. Check 'Detailed Logs'")
        print("5. Restart MTG Arena")
        return
    
    print(f"Found log file: {reader.log_path}")
    
    # Register a callback for draft picks
    reader.register_callback('draft_pick', example_callback)
    
    # Get recent events
    print("\nReading recent events...")
    recent_events = reader.get_recent_events(50)
    print(f"Found {len(recent_events)} recent events")
    
    if recent_events:
        print("\nSample events:")
        for event in recent_events[:5]:
            print(f"  - {event['type']}: {event.get('raw_line', '')[:80]}")
    
    # Start monitoring (uncomment to enable real-time monitoring)
    # print("\nStarting real-time monitoring...")
    # reader.start_monitoring(interval=0.5)


if __name__ == "__main__":
    main()

