#!/usr/bin/env python3
"""
Query Processor for MTG Draft Coach RAG System

Parses user queries to extract:
- Intent (card evaluation, archetype comparison, draft strategy, etc.)
- Entities (card names, archetypes, set codes, metrics)
- Query type (single card, comparison, archetype, strategy)

Supports multiple input sources: terminal, files, CSV, and extensible for GUI.
"""

import re
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import csv
import json


class QueryIntent(Enum):
    """Types of query intents."""
    CARD_EVALUATION = "card_evaluation"  # "Tell me about X"
    CARD_COMPARISON = "card_comparison"  # "Compare X vs Y"
    ARCHETYPE_QUERY = "archetype_query"  # "What's the best WU deck?"
    ARCHETYPE_EXPLANATION = "archetype_explanation"  # "What does WU do in TLA?"
    DRAFT_STRATEGY = "draft_strategy"  # "What should I pick first?"
    DRAFT_DIRECTION = "draft_direction"  # "What direction should I draft?"
    PICK_ADVICE = "pick_advice"  # "Should I pick X or Y?"
    PICK_SPECIFIC = "pick_specific"  # "What should I pick at pick 5?"
    DECK_BUILDING = "deck_building"  # "What deck should I build?"
    STATISTICS_QUERY = "statistics_query"  # "What's the win rate of X?"
    FOLLOW_UP = "follow_up"  # "Tell me more", "What about X?"
    ELABORATION = "elaboration"  # "Why?", "Explain that", "How does that work?"
    GENERAL = "general"  # General MTG/draft question


class QueryType(Enum):
    """Types of queries."""
    SINGLE_CARD = "single_card"
    MULTI_CARD = "multi_card"
    ARCHETYPE = "archetype"
    ARCHETYPE_EXPLANATION = "archetype_explanation"
    COMPARISON = "comparison"
    STRATEGY = "strategy"
    DRAFT_DIRECTION = "draft_direction"
    PICK_SPECIFIC = "pick_specific"
    DECK_BUILDING = "deck_building"
    STATISTICS = "statistics"
    FOLLOW_UP = "follow_up"
    ELABORATION = "elaboration"
    GENERAL = "general"


@dataclass
class ExtractedEntities:
    """Extracted entities from a query."""
    cards: List[str] = field(default_factory=list)
    archetypes: List[str] = field(default_factory=list)  # Color combinations like "WU", "URG"
    set_codes: List[str] = field(default_factory=list)  # Set codes like "TLA", "MOM"
    metrics: List[str] = field(default_factory=list)  # "win rate", "pick number", etc.
    ranks: List[str] = field(default_factory=list)  # "bronze", "mythic", etc.
    event_types: List[str] = field(default_factory=list)  # "PremierDraft", "QuickDraft"
    pick_numbers: List[int] = field(default_factory=list)  # Pick numbers (0-14)
    pack_numbers: List[int] = field(default_factory=list)  # Pack numbers (0-2)
    draft_positions: List[str] = field(default_factory=list)  # "early", "mid", "late", "first", "last"
    
    def __str__(self):
        parts = []
        if self.cards:
            parts.append(f"Cards: {self.cards}")
        if self.archetypes:
            parts.append(f"Archetypes: {self.archetypes}")
        if self.set_codes:
            parts.append(f"Sets: {self.set_codes}")
        if self.pick_numbers:
            parts.append(f"Picks: {self.pick_numbers}")
        if self.pack_numbers:
            parts.append(f"Packs: {self.pack_numbers}")
        if self.draft_positions:
            parts.append(f"Positions: {self.draft_positions}")
        return ", ".join(parts) if parts else "No entities"


@dataclass
class ProcessedQuery:
    """Processed query with all extracted information."""
    original_query: str
    normalized_query: str
    intent: QueryIntent
    query_type: QueryType
    entities: ExtractedEntities
    confidence: float = 0.0  # Confidence score 0-1
    is_follow_up: bool = False  # Is this a follow-up to a previous query?
    context_references: List[str] = field(default_factory=list)  # References to previous context
    enrichment: Optional[Any] = None  # QueryEnrichment object if preprocessing enabled
    
    def __str__(self):
        follow_up_str = " [FOLLOW-UP]" if self.is_follow_up else ""
        return f"Intent: {self.intent.value}, Type: {self.query_type.value}, {self.entities}{follow_up_str}"


class InputHandler(ABC):
    """Abstract base class for input handlers."""
    
    @abstractmethod
    def read_input(self) -> List[str]:
        """Read input and return list of query strings."""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return name of input source."""
        pass


class TerminalInputHandler(InputHandler):
    """Handle input from terminal/command line."""
    
    def __init__(self, prompt: str = "Enter your question (or 'quit' to exit): "):
        self.prompt = prompt
    
    def read_input(self) -> List[str]:
        """Read input from terminal."""
        queries = []
        print("\n" + "=" * 80)
        print("MTG DRAFT COACH - Query Interface")
        print("=" * 80)
        print("Type 'quit' or 'exit' to stop\n")
        
        while True:
            try:
                query = input(self.prompt).strip()
                if not query:
                    continue
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                queries.append(query)
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break
        
        return queries
    
    def get_source_name(self) -> str:
        return "terminal"


class FileInputHandler(InputHandler):
    """Handle input from text file (one query per line)."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
    
    def read_input(self) -> List[str]:
        """Read queries from file (one per line)."""
        queries = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):  # Skip empty lines and comments
                    queries.append(line)
        return queries
    
    def get_source_name(self) -> str:
        return f"file:{self.file_path.name}"


class CSVInputHandler(InputHandler):
    """Handle input from CSV file."""
    
    def __init__(self, file_path: str, query_column: str = "query"):
        self.file_path = Path(file_path)
        self.query_column = query_column
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    def read_input(self) -> List[str]:
        """Read queries from CSV file."""
        queries = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if self.query_column not in reader.fieldnames:
                raise ValueError(f"Column '{self.query_column}' not found in CSV. Available columns: {reader.fieldnames}")
            
            for row in reader:
                query = row.get(self.query_column, '').strip()
                if query:
                    queries.append(query)
        return queries
    
    def get_source_name(self) -> str:
        return f"csv:{self.file_path.name}"


class JSONInputHandler(InputHandler):
    """Handle input from JSON file."""
    
    def __init__(self, file_path: str, query_key: str = "query"):
        self.file_path = Path(file_path)
        self.query_key = query_key
        if not self.file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    def read_input(self) -> List[str]:
        """Read queries from JSON file."""
        queries = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Handle both list of queries and single query
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        queries.append(item)
                    elif isinstance(item, dict) and self.query_key in item:
                        queries.append(item[self.query_key])
            elif isinstance(data, dict):
                if self.query_key in data:
                    if isinstance(data[self.query_key], list):
                        queries.extend(data[self.query_key])
                    else:
                        queries.append(data[self.query_key])
        
        return queries
    
    def get_source_name(self) -> str:
        return f"json:{self.file_path.name}"


class ConversationContext:
    """Tracks conversation context for follow-up queries."""
    
    def __init__(self):
        self.previous_queries: List[ProcessedQuery] = []
        self.previous_entities: ExtractedEntities = ExtractedEntities()
        self.previous_intent: Optional[QueryIntent] = None
        self.max_context_length = 10  # Keep last 10 queries
    
    def add_query(self, processed_query: ProcessedQuery):
        """Add a processed query to context."""
        self.previous_queries.append(processed_query)
        if len(self.previous_queries) > self.max_context_length:
            self.previous_queries.pop(0)
        
        # Update aggregated context
        if processed_query.entities.cards:
            self.previous_entities.cards.extend(processed_query.entities.cards)
        if processed_query.entities.archetypes:
            self.previous_entities.archetypes.extend(processed_query.entities.archetypes)
        if processed_query.entities.set_codes:
            self.previous_entities.set_codes.extend(processed_query.entities.set_codes)
        
        self.previous_intent = processed_query.intent
    
    def clear(self):
        """Clear conversation context."""
        self.previous_queries = []
        self.previous_entities = ExtractedEntities()
        self.previous_intent = None
    
    def get_recent_entities(self) -> ExtractedEntities:
        """Get entities from recent queries."""
        if not self.previous_queries:
            return ExtractedEntities()
        
        # Get entities from last query
        return self.previous_queries[-1].entities


class QueryProcessor:
    """Main query processor that extracts intent and entities."""
    
    # Common MTG set codes (3-letter codes)
    SET_CODES = {
        'tla', 'mom', 'bro', 'dmu', 'snc', 'neo', 'vow', 'mid', 'afr', 'stx',
        'khm', 'znr', 'iko', 'thb', 'eld', 'war', 'rna', 'grn', 'dom', 'rix'
    }
    
    # Color combinations (archetypes)
    COLOR_COMBINATIONS = {
        'w', 'u', 'b', 'r', 'g',  # Single colors
        'wu', 'wb', 'wr', 'wg', 'ub', 'ur', 'ug', 'br', 'bg', 'rg',  # Two colors
        'wub', 'wur', 'wug', 'wbr', 'wbg', 'wrg', 'ubr', 'ubg', 'urg', 'brg',  # Three colors
        'wubr', 'wubg', 'wurg', 'wbrg', 'ubrg', 'wubrg'  # Four+ colors
    }
    
    # Comparison keywords
    COMPARISON_KEYWORDS = ['vs', 'versus', 'compare', 'comparison', 'better', 'best', 'or', 'versus']
    
    # Strategy keywords
    STRATEGY_KEYWORDS = ['should i', 'what should', 'how to', 'advice', 'recommend', 'suggest', 'pick', 'draft']
    
    # Statistics keywords
    STATS_KEYWORDS = ['win rate', 'wr', 'gih', 'drawn', 'pick number', 'average', 'statistics', 'stats', 'performance']
    
    # Pick-specific keywords
    PICK_SPECIFIC_KEYWORDS = ['pick', 'pack', 'pick number', 'pack number', 'at pick', 'pick #', 'pack #', 
                              'first pick', 'last pick', 'early pick', 'late pick', 'mid pick']
    
    # Deck building keywords
    DECK_BUILDING_KEYWORDS = ['build', 'deck', 'construct', 'make a deck', 'deck list', 'decklist', 
                              'what deck', 'which deck', 'deck to build']
    
    # Draft direction keywords
    DRAFT_DIRECTION_KEYWORDS = ['direction', 'what direction', 'which direction', 'where to go', 
                                'what colors', 'which colors', 'commit', 'commit to', 'stay open']
    
    # Archetype explanation keywords
    ARCHETYPE_EXPLANATION_KEYWORDS = ['what does', 'how does', 'what is', 'explain', 'describe', 
                                      'how does work', 'what does do', 'archetype', 'deck type']
    
    # Follow-up keywords
    FOLLOW_UP_KEYWORDS = ['tell me more', 'more about', 'what about', 'also', 'and', 'additionally',
                          'furthermore', 'more info', 'more information', 'elaborate']
    
    # Elaboration keywords
    ELABORATION_KEYWORDS = ['why', 'how', 'explain', 'elaborate', 'clarify', 'what do you mean',
                            'can you explain', 'how does that', 'why is that', 'what makes']
    
    def __init__(self, db_path: str = "mtg_draft_coach.db", enable_context: bool = True):
        """Initialize query processor with database connection."""
        self.db_path = Path(db_path)
        self.card_cache: Dict[str, List[str]] = {}  # Cache card names by set
        self.enable_context = enable_context
        self.context = ConversationContext() if enable_context else None
        self._load_card_names()
    
    def _load_card_names(self):
        """Load all card names from database for matching."""
        if not self.db_path.exists():
            return
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT card_name, "set" FROM cards')
                for card_name, set_code in cursor.fetchall():
                    if set_code not in self.card_cache:
                        self.card_cache[set_code] = []
                    self.card_cache[set_code].append(card_name)
        except Exception as e:
            print(f"Warning: Could not load card names from database: {e}")
    
    def normalize_query(self, query: str) -> str:
        """Normalize query text."""
        # Lowercase and strip
        normalized = query.lower().strip()
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def extract_set_codes(self, query: str) -> List[str]:
        """Extract set codes from query."""
        found_sets = []
        query_lower = query.lower()
        
        # Look for 3-letter set codes (uppercase or lowercase)
        set_pattern = r'\b([A-Z]{3}|[a-z]{3})\b'
        matches = re.findall(set_pattern, query)
        
        for match in matches:
            set_code = match.upper()
            if set_code.lower() in self.SET_CODES:
                if set_code not in found_sets:
                    found_sets.append(set_code)
        
        return found_sets
    
    def extract_archetypes(self, query: str) -> List[str]:
        """Extract color combinations (archetypes) from query."""
        found_archetypes = []
        query_lower = query.lower()
        
        # Color name patterns
        color_map = {
            'white': 'w', 'blue': 'u', 'black': 'b', 'red': 'r', 'green': 'g',
            'w': 'w', 'u': 'u', 'b': 'b', 'r': 'r', 'g': 'g'
        }
        
        # Look for color combinations
        # Pattern: "WU", "White Blue", "W/U", "WU deck", etc.
        patterns = [
            r'\b([wubrg]{2,5})\b',  # Direct like "WU", "URG"
            r'\b([wubrg]/[wubrg])\b',  # Like "W/U"
            r'(white|blue|black|red|green)\s+(white|blue|black|red|green)',  # "white blue"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                if isinstance(match, tuple):
                    # Convert color names to letters
                    archetype = ''.join(sorted([color_map.get(c.lower(), c.lower()) for c in match if c.lower() in color_map]))
                else:
                    archetype = match.replace('/', '').upper()
                
                if archetype and len(archetype) >= 2:
                    # Normalize to WUBRG order
                    archetype = self._normalize_color_order(archetype)
                    if archetype not in found_archetypes:
                        found_archetypes.append(archetype)
        
        return found_archetypes
    
    def _normalize_color_order(self, colors: str) -> str:
        """Normalize color combination to WUBRG order."""
        color_order = {'W': 0, 'U': 1, 'B': 2, 'R': 3, 'G': 4}
        sorted_colors = sorted(colors.upper(), key=lambda c: color_order.get(c, 99))
        return ''.join(sorted_colors)
    
    def extract_card_names(self, query: str, set_code: Optional[str] = None) -> List[str]:
        """Extract card names from query using database lookup."""
        found_cards = []
        query_lower = query.lower()
        
        # Get card names to search
        cards_to_search = []
        if set_code and set_code in self.card_cache:
            cards_to_search = self.card_cache[set_code]
        else:
            # Search all sets
            for set_cards in self.card_cache.values():
                cards_to_search.extend(set_cards)
        
        # Remove duplicates
        cards_to_search = list(set(cards_to_search))
        
        # Try exact matches first (quoted strings)
        quoted_pattern = r'"([^"]+)"|\'([^\']+)\''
        quoted_matches = re.findall(quoted_pattern, query)
        for match in quoted_matches:
            card_name = (match[0] or match[1]).lower().strip()
            if card_name in cards_to_search:
                if card_name not in found_cards:
                    found_cards.append(card_name)
        
        # Try fuzzy matching for card names in query
        query_words = set(query_lower.split())
        
        for card_name in cards_to_search:
            card_words = set(card_name.split())
            
            # Check if all significant words of card name appear in query
            # (skip common words like "the", "a", "of")
            significant_words = [w for w in card_words if len(w) > 2]
            if significant_words:
                matches = sum(1 for word in significant_words if word in query_words)
                if matches >= len(significant_words) * 0.7:  # 70% match threshold
                    if card_name not in found_cards:
                        found_cards.append(card_name)
        
        # Also try direct word matching for common card name patterns
        for card_name in cards_to_search:
            # Check if card name appears as substring (for multi-word cards)
            if card_name in query_lower or query_lower in card_name:
                if card_name not in found_cards:
                    found_cards.append(card_name)
        
        return found_cards
    
    def extract_metrics(self, query: str) -> List[str]:
        """Extract metric mentions from query."""
        found_metrics = []
        query_lower = query.lower()
        
        metric_keywords = {
            'win rate': 'win_rate',
            'gih wr': 'gih_wr',
            'gih': 'gih_wr',
            'drawn wr': 'drawn_wr',
            'drawn': 'drawn_wr',
            'overall wr': 'overall_wr',
            'overall': 'overall_wr',
            'pick number': 'pick_number',
            'pick': 'pick_number',
            'maindeck rate': 'maindeck_rate',
            'maindeck': 'maindeck_rate',
            'sideboard rate': 'sideboard_rate',
            'sideboard': 'sideboard_rate',
            'cmc': 'cmc',
            'mana cost': 'cmc',
            'color identity': 'color_identity',
            'colors': 'color_identity',
            'rarity': 'rarity'
        }
        
        for keyword, metric in metric_keywords.items():
            if keyword in query_lower:
                if metric not in found_metrics:
                    found_metrics.append(metric)
        
        return found_metrics
    
    def extract_ranks(self, query: str) -> List[str]:
        """Extract rank mentions from query."""
        found_ranks = []
        query_lower = query.lower()
        
        ranks = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'mythic']
        for rank in ranks:
            if rank in query_lower:
                found_ranks.append(rank)
        
        return found_ranks
    
    def extract_pick_numbers(self, query: str) -> List[int]:
        """Extract pick numbers from query (0-14)."""
        found_picks = []
        query_lower = query.lower()
        
        # Patterns: "pick 5", "pick #5", "pick number 5", "5th pick", "at pick 5"
        patterns = [
            r'pick\s*(?:number|#)?\s*(\d+)',
            r'(\d+)(?:st|nd|rd|th)?\s*pick',
            r'at\s*pick\s*(\d+)',
            r'pick\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                try:
                    pick_num = int(match)
                    if 0 <= pick_num <= 14:  # Valid pick range
                        if pick_num not in found_picks:
                            found_picks.append(pick_num)
                except ValueError:
                    pass
        
        return sorted(found_picks)
    
    def extract_pack_numbers(self, query: str) -> List[int]:
        """Extract pack numbers from query (0-2)."""
        found_packs = []
        query_lower = query.lower()
        
        # Patterns: "pack 1", "pack #1", "pack number 1", "1st pack", "in pack 1"
        patterns = [
            r'pack\s*(?:number|#)?\s*(\d+)',
            r'(\d+)(?:st|nd|rd|th)?\s*pack',
            r'in\s*pack\s*(\d+)',
            r'pack\s*(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                try:
                    pack_num = int(match) - 1  # Convert 1-based to 0-based
                    if 0 <= pack_num <= 2:  # Valid pack range
                        if pack_num not in found_packs:
                            found_packs.append(pack_num)
                except ValueError:
                    pass
        
        return sorted(found_packs)
    
    def extract_draft_positions(self, query: str) -> List[str]:
        """Extract draft position indicators (early, mid, late, first, last)."""
        found_positions = []
        query_lower = query.lower()
        
        position_keywords = {
            'early': 'early',
            'mid': 'mid',
            'middle': 'mid',
            'late': 'late',
            'first': 'first',
            'last': 'last',
            'beginning': 'early',
            'end': 'late',
            'start': 'early',
        }
        
        for keyword, position in position_keywords.items():
            if keyword in query_lower:
                if position not in found_positions:
                    found_positions.append(position)
        
        return found_positions
    
    def detect_follow_up(self, query: str) -> Tuple[bool, List[str]]:
        """Detect if query is a follow-up and extract context references."""
        query_lower = query.lower().strip()
        is_follow_up = False
        references = []
        
        # Check for follow-up patterns
        follow_up_patterns = [
            r'what about (.+)',
            r'and (.+)',
            r'also (.+)',
            r'tell me more (?:about )?(.+)',
            r'more about (.+)',
            r'what (.+)',
            r'how about (.+)',
        ]
        
        # Check for elaboration patterns
        if any(keyword in query_lower for keyword in self.ELABORATION_KEYWORDS):
            is_follow_up = True
        
        # Check for follow-up keywords
        if any(keyword in query_lower for keyword in self.FOLLOW_UP_KEYWORDS):
            is_follow_up = True
        
        # Check for very short queries (likely follow-ups)
        if len(query.split()) <= 3 and query_lower not in ['quit', 'exit', 'help']:
            is_follow_up = True
        
        # Extract references
        for pattern in follow_up_patterns:
            matches = re.findall(pattern, query_lower)
            references.extend(matches)
        
        return is_follow_up, references
    
    def classify_intent(self, query: str, entities: ExtractedEntities, is_follow_up: bool = False) -> QueryIntent:
        """Classify the intent of the query."""
        query_lower = query.lower()
        
        # Check for follow-up first
        if is_follow_up:
            if any(keyword in query_lower for keyword in self.ELABORATION_KEYWORDS):
                return QueryIntent.ELABORATION
            return QueryIntent.FOLLOW_UP
        
        # Check for pick-specific queries
        if entities.pick_numbers or entities.pack_numbers or entities.draft_positions:
            if any(keyword in query_lower for keyword in self.PICK_SPECIFIC_KEYWORDS):
                return QueryIntent.PICK_SPECIFIC
        
        # Check for deck building
        if any(keyword in query_lower for keyword in self.DECK_BUILDING_KEYWORDS):
            return QueryIntent.DECK_BUILDING
        
        # Check for draft direction
        if any(keyword in query_lower for keyword in self.DRAFT_DIRECTION_KEYWORDS):
            return QueryIntent.DRAFT_DIRECTION
        
        # Check for archetype explanation
        if entities.archetypes and any(keyword in query_lower for keyword in self.ARCHETYPE_EXPLANATION_KEYWORDS):
            return QueryIntent.ARCHETYPE_EXPLANATION
        
        # Check for comparison
        if any(keyword in query_lower for keyword in self.COMPARISON_KEYWORDS):
            if len(entities.cards) >= 2:
                return QueryIntent.CARD_COMPARISON
            elif len(entities.archetypes) >= 2:
                return QueryIntent.ARCHETYPE_QUERY
        
        # Check for pick advice
        if any(keyword in query_lower for keyword in self.STRATEGY_KEYWORDS):
            if 'pick' in query_lower or 'draft' in query_lower:
                return QueryIntent.PICK_ADVICE
            return QueryIntent.DRAFT_STRATEGY
        
        # Check for statistics
        if any(keyword in query_lower for keyword in self.STATS_KEYWORDS):
            return QueryIntent.STATISTICS_QUERY
        
        # Check for archetype query
        if entities.archetypes:
            return QueryIntent.ARCHETYPE_QUERY
        
        # Check for single card
        if len(entities.cards) == 1:
            return QueryIntent.CARD_EVALUATION
        
        # Check for multi-card
        if len(entities.cards) > 1:
            return QueryIntent.CARD_COMPARISON
        
        # Default to general
        return QueryIntent.GENERAL
    
    def determine_query_type(self, intent: QueryIntent, entities: ExtractedEntities) -> QueryType:
        """Determine the query type based on intent and entities."""
        intent_to_type = {
            QueryIntent.CARD_EVALUATION: QueryType.SINGLE_CARD,
            QueryIntent.CARD_COMPARISON: QueryType.COMPARISON,
            QueryIntent.ARCHETYPE_QUERY: QueryType.ARCHETYPE,
            QueryIntent.ARCHETYPE_EXPLANATION: QueryType.ARCHETYPE_EXPLANATION,
            QueryIntent.DRAFT_STRATEGY: QueryType.STRATEGY,
            QueryIntent.DRAFT_DIRECTION: QueryType.DRAFT_DIRECTION,
            QueryIntent.PICK_ADVICE: QueryType.STRATEGY,
            QueryIntent.PICK_SPECIFIC: QueryType.PICK_SPECIFIC,
            QueryIntent.DECK_BUILDING: QueryType.DECK_BUILDING,
            QueryIntent.STATISTICS_QUERY: QueryType.STATISTICS,
            QueryIntent.FOLLOW_UP: QueryType.FOLLOW_UP,
            QueryIntent.ELABORATION: QueryType.ELABORATION,
            QueryIntent.GENERAL: QueryType.GENERAL,
        }
        return intent_to_type.get(intent, QueryType.GENERAL)
    
    def calculate_confidence(self, entities: ExtractedEntities, intent: QueryIntent, is_follow_up: bool = False) -> float:
        """Calculate confidence score for the processed query."""
        confidence = 0.0
        
        # Base confidence
        if entities.cards:
            confidence += 0.25
        if entities.archetypes:
            confidence += 0.2
        if entities.set_codes:
            confidence += 0.1
        if entities.pick_numbers or entities.pack_numbers:
            confidence += 0.15
        if entities.draft_positions:
            confidence += 0.1
        
        # Intent-specific confidence
        if intent != QueryIntent.GENERAL:
            confidence += 0.2
        
        # Follow-up queries have higher confidence if context exists
        if is_follow_up and self.context and self.context.previous_queries:
            confidence += 0.15
        
        # Multiple entities increase confidence
        if len(entities.cards) > 1:
            confidence += 0.1
        if entities.metrics:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def preprocess_for_ai(self, processed_query: ProcessedQuery):
        """Preprocess query for AI model using enhancement module."""
        try:
            from rag.query_preprocessor_enhancements import QueryPreprocessor
            preprocessor = QueryPreprocessor(self.db_path, self.card_cache)
            return preprocessor.preprocess(processed_query.original_query, processed_query)
        except ImportError:
            # Fallback if enhancements not available
            return None
    
    def process(self, query: str, use_context: bool = True, enable_preprocessing: bool = False) -> ProcessedQuery:
        """Process a query and extract all information."""
        try:
            normalized = self.normalize_query(query)
            
            # Detect follow-up
            is_follow_up, context_refs = self.detect_follow_up(query)
            
            # Extract entities
            entities = ExtractedEntities()
            entities.set_codes = self.extract_set_codes(query)
            entities.archetypes = self.extract_archetypes(query)
            entities.cards = self.extract_card_names(query, entities.set_codes[0] if entities.set_codes else None)
            entities.metrics = self.extract_metrics(query)
            entities.ranks = self.extract_ranks(query)
            entities.pick_numbers = self.extract_pick_numbers(query)
            entities.pack_numbers = self.extract_pack_numbers(query)
            entities.draft_positions = self.extract_draft_positions(query)
            
            # If follow-up and context enabled, merge with previous entities
            if is_follow_up and use_context and self.context and self.context.previous_queries:
                prev_entities = self.context.get_recent_entities()
                # Merge entities (prefer new ones, but fill in from context)
                if not entities.cards and prev_entities.cards:
                    entities.cards = prev_entities.cards[:]  # Copy list
                if not entities.archetypes and prev_entities.archetypes:
                    entities.archetypes = prev_entities.archetypes[:]
                if not entities.set_codes and prev_entities.set_codes:
                    entities.set_codes = prev_entities.set_codes[:]
            
            # Classify intent
            intent = self.classify_intent(query, entities, is_follow_up)
            
            # Determine query type
            query_type = self.determine_query_type(intent, entities)
            
            # Calculate confidence
            confidence = self.calculate_confidence(entities, intent, is_follow_up)
            
            processed = ProcessedQuery(
                original_query=query,
                normalized_query=normalized,
                intent=intent,
                query_type=query_type,
                entities=entities,
                confidence=confidence,
                is_follow_up=is_follow_up,
                context_references=context_refs
            )
            
            # Add to context if enabled
            if use_context and self.context:
                self.context.add_query(processed)
            
            # Apply preprocessing if enabled
            if enable_preprocessing:
                try:
                    enrichment = self.preprocess_for_ai(processed)
                    if enrichment:
                        # Attach enrichment to processed query
                        processed.enrichment = enrichment
                except Exception as e:
                    print(f"Warning: Preprocessing failed: {e}")
            
            return processed
            
        except Exception as e:
            # Robust error handling - return a general query on error
            print(f"Warning: Error processing query '{query}': {e}")
            return ProcessedQuery(
                original_query=query,
                normalized_query=query.lower().strip(),
                intent=QueryIntent.GENERAL,
                query_type=QueryType.GENERAL,
                entities=ExtractedEntities(),
                confidence=0.1
            )


class QueryProcessorInterface:
    """High-level interface for processing queries from multiple sources."""
    
    def __init__(self, db_path: str = "mtg_draft_coach.db", input_handler: Optional[InputHandler] = None, 
                 enable_context: bool = True):
        """
        Initialize query processor interface.
        
        Args:
            db_path: Path to SQLite database
            input_handler: Input handler (if None, uses TerminalInputHandler)
            enable_context: Enable conversation context tracking
        """
        self.processor = QueryProcessor(db_path, enable_context=enable_context)
        self.input_handler = input_handler or TerminalInputHandler()
        self.enable_context = enable_context
    
    def set_input_handler(self, handler: InputHandler):
        """Set a different input handler."""
        self.input_handler = handler
    
    def process_queries(self) -> List[ProcessedQuery]:
        """Read queries from input source and process them."""
        queries = self.input_handler.read_input()
        processed = []
        
        print(f"\nProcessing {len(queries)} query/queries from {self.input_handler.get_source_name()}...")
        
        for i, query in enumerate(queries, 1):
            print(f"\n[{i}/{len(queries)}] Processing: {query}")
            processed_query = self.processor.process(query)
            processed.append(processed_query)
            self._print_processed_query(processed_query)
        
        return processed
    
    def process_single_query(self, query: str) -> ProcessedQuery:
        """Process a single query string."""
        return self.processor.process(query)
    
    def clear_context(self):
        """Clear conversation context."""
        if self.processor.context:
            self.processor.context.clear()
    
    def _print_processed_query(self, processed: ProcessedQuery):
        """Print processed query information."""
        follow_up_indicator = " [FOLLOW-UP]" if processed.is_follow_up else ""
        print(f"  Intent: {processed.intent.value}{follow_up_indicator}")
        print(f"  Type: {processed.query_type.value}")
        print(f"  Confidence: {processed.confidence:.2f}")
        print(f"  Entities:")
        if processed.entities.cards:
            print(f"    Cards: {', '.join(processed.entities.cards)}")
        if processed.entities.archetypes:
            print(f"    Archetypes: {', '.join(processed.entities.archetypes)}")
        if processed.entities.set_codes:
            print(f"    Sets: {', '.join(processed.entities.set_codes)}")
        if processed.entities.pick_numbers:
            print(f"    Pick Numbers: {processed.entities.pick_numbers}")
        if processed.entities.pack_numbers:
            print(f"    Pack Numbers: {processed.entities.pack_numbers}")
        if processed.entities.draft_positions:
            print(f"    Draft Positions: {', '.join(processed.entities.draft_positions)}")
        if processed.entities.metrics:
            print(f"    Metrics: {', '.join(processed.entities.metrics)}")
        if processed.entities.ranks:
            print(f"    Ranks: {', '.join(processed.entities.ranks)}")
        if processed.context_references:
            print(f"    Context References: {', '.join(processed.context_references)}")


def main():
    """Main entry point for command-line usage."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MTG Draft Coach Query Processor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive terminal mode
  python query_processor.py
  
  # Process from file
  python query_processor.py --file queries.txt
  
  # Process from CSV
  python query_processor.py --csv queries.csv --column query
  
  # Process from JSON
  python query_processor.py --json queries.json
  
  # Process single query
  python query_processor.py --query "What's the win rate of Invasion Submersible?"
        """
    )
    
    parser.add_argument('--db', default='mtg_draft_coach.db', help='Path to database')
    parser.add_argument('--query', help='Process a single query')
    parser.add_argument('--file', help='Process queries from text file (one per line)')
    parser.add_argument('--csv', help='Process queries from CSV file')
    parser.add_argument('--csv-column', default='query', help='Column name in CSV (default: query)')
    parser.add_argument('--json', help='Process queries from JSON file')
    parser.add_argument('--json-key', default='query', help='Key name in JSON (default: query)')
    
    args = parser.parse_args()
    
    # Determine input handler
    handler = None
    if args.query:
        # Single query mode
        processor = QueryProcessor(args.db)
        processed = processor.process(args.query)
        print("\n" + "=" * 80)
        print("PROCESSED QUERY")
        print("=" * 80)
        print(f"Original: {processed.original_query}")
        print(f"Intent: {processed.intent.value}")
        print(f"Type: {processed.query_type.value}")
        print(f"Confidence: {processed.confidence:.2f}")
        print(f"Entities: {processed.entities}")
        return
    elif args.file:
        handler = FileInputHandler(args.file)
    elif args.csv:
        handler = CSVInputHandler(args.csv, args.csv_column)
    elif args.json:
        handler = JSONInputHandler(args.json, args.json_key)
    else:
        # Default to terminal
        handler = TerminalInputHandler()
    
    # Process queries
    interface = QueryProcessorInterface(args.db, handler)
    processed_queries = interface.process_queries()
    
    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    print(f"Total queries processed: {len(processed_queries)}")
    
    intent_counts = {}
    for pq in processed_queries:
        intent = pq.intent.value
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
    
    print("\nIntent distribution:")
    for intent, count in sorted(intent_counts.items()):
        print(f"  {intent}: {count}")


if __name__ == "__main__":
    main()

