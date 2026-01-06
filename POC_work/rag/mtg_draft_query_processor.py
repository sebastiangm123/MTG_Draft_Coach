#!/usr/bin/env python3
"""
MTG Draft Coach - Unified Query Processor for RAG System

This is the complete, unified query processor that combines all preprocessing,
entity extraction, intent classification, and enrichment capabilities for
Magic: The Gathering draft coaching queries.

Features:
- Handles any draft-related question
- Expands abbreviations and normalizes queries
- Extracts all entities (cards, archetypes, sets, picks, packs, etc.)
- Classifies intent and query type
- Detects ambiguities and generates clarifications
- Provides AI and retrieval hints
- Maintains conversation context
- Validates entities against database
- Supports multiple input sources
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


# ============================================================================
# ENUMS
# ============================================================================

class QueryIntent(Enum):
    """Types of query intents."""
    CARD_EVALUATION = "card_evaluation"
    CARD_COMPARISON = "card_comparison"
    ARCHETYPE_QUERY = "archetype_query"
    ARCHETYPE_EXPLANATION = "archetype_explanation"
    DRAFT_STRATEGY = "draft_strategy"
    DRAFT_DIRECTION = "draft_direction"
    PICK_ADVICE = "pick_advice"
    PICK_SPECIFIC = "pick_specific"
    DECK_BUILDING = "deck_building"
    STATISTICS_QUERY = "statistics_query"
    FOLLOW_UP = "follow_up"
    ELABORATION = "elaboration"
    GENERAL = "general"


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


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class AmbiguityType(Enum):
    """Types of ambiguity in queries."""
    NONE = "none"
    CARD_NAME = "card_name"
    ARCHETYPE = "archetype"
    METRIC = "metric"
    INTENT = "intent"
    MULTIPLE = "multiple"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ExtractedEntities:
    """Extracted entities from a query."""
    cards: List[str] = field(default_factory=list)
    archetypes: List[str] = field(default_factory=list)
    set_codes: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    ranks: List[str] = field(default_factory=list)
    event_types: List[str] = field(default_factory=list)
    pick_numbers: List[int] = field(default_factory=list)
    pack_numbers: List[int] = field(default_factory=list)
    draft_positions: List[str] = field(default_factory=list)
    
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
class QueryEnrichment:
    """Enriched query information for AI processing."""
    original_query: str
    normalized_query: str
    expanded_query: str
    rewritten_query: str
    complexity: QueryComplexity
    ambiguity: AmbiguityType
    ambiguity_details: List[str] = field(default_factory=list)
    requires_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    ai_hints: Dict[str, any] = field(default_factory=dict)
    retrieval_hints: Dict[str, any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    is_multi_query: bool = False
    sub_queries: List[str] = field(default_factory=list)


@dataclass
class ProcessedQuery:
    """Complete processed query with all information."""
    original_query: str
    normalized_query: str
    expanded_query: str
    rewritten_query: str
    intent: QueryIntent
    query_type: QueryType
    entities: ExtractedEntities
    confidence: float = 0.0
    is_follow_up: bool = False
    context_references: List[str] = field(default_factory=list)
    complexity: QueryComplexity = QueryComplexity.SIMPLE
    ambiguity: AmbiguityType = AmbiguityType.NONE
    ambiguity_details: List[str] = field(default_factory=list)
    requires_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)
    ai_hints: Dict[str, any] = field(default_factory=dict)
    retrieval_hints: Dict[str, any] = field(default_factory=dict)
    validation_errors: List[str] = field(default_factory=list)
    is_multi_query: bool = False
    sub_queries: List[str] = field(default_factory=list)
    
    def __str__(self):
        follow_up_str = " [FOLLOW-UP]" if self.is_follow_up else ""
        return f"Intent: {self.intent.value}, Type: {self.query_type.value}, {self.entities}{follow_up_str}"


# ============================================================================
# INPUT HANDLERS
# ============================================================================

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
    """Handle input from text file."""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
    
    def read_input(self) -> List[str]:
        """Read queries from file."""
        queries = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    queries.append(line)
        return queries
    
    def get_source_name(self) -> str:
        return f"file:{self.file_path.name}"


# ============================================================================
# CONVERSATION CONTEXT
# ============================================================================

class ConversationContext:
    """Tracks conversation context for follow-up queries."""
    
    def __init__(self):
        self.previous_queries: List[ProcessedQuery] = []
        self.max_context_length = 10
    
    def add_query(self, processed_query: ProcessedQuery):
        """Add a processed query to context."""
        self.previous_queries.append(processed_query)
        if len(self.previous_queries) > self.max_context_length:
            self.previous_queries.pop(0)
    
    def get_recent_entities(self) -> ExtractedEntities:
        """Get entities from recent queries."""
        if not self.previous_queries:
            return ExtractedEntities()
        return self.previous_queries[-1].entities
    
    def clear(self):
        """Clear conversation context."""
        self.previous_queries = []


# ============================================================================
# UNIFIED MTG DRAFT QUERY PROCESSOR
# ============================================================================

class MTGDraftQueryProcessor:
    """
    Unified Query Processor for MTG Draft Coach RAG System.
    
    This processor handles all aspects of query processing:
    - Abbreviation expansion
    - Query normalization and rewriting
    - Entity extraction (cards, archetypes, sets, picks, packs)
    - Intent classification
    - Ambiguity detection
    - Complexity analysis
    - Entity validation
    - AI and retrieval hint generation
    - Conversation context management
    """
    
    # MTG Set Codes
    SET_CODES = {
        'tla', 'mom', 'bro', 'dmu', 'snc', 'neo', 'vow', 'mid', 'afr', 'stx',
        'khm', 'znr', 'iko', 'thb', 'eld', 'war', 'rna', 'grn', 'dom', 'rix'
    }
    
    # Abbreviations
    ABBREVIATIONS = {
        'wr': 'win rate', 'gih': 'games in hand', 'gih wr': 'games in hand win rate',
        'p1p1': 'pack 1 pick 1', 'p1p2': 'pack 1 pick 2', 'p2p1': 'pack 2 pick 1',
        'cmc': 'converted mana cost', 'md': 'maindeck', 'sb': 'sideboard',
        'otp': 'on the play', 'otd': 'on the draw', 'avg': 'average',
    }
    
    # Keywords
    COMPARISON_KEYWORDS = ['vs', 'versus', 'compare', 'better', 'best', 'or']
    STRATEGY_KEYWORDS = ['should i', 'what should', 'how to', 'advice', 'recommend', 'suggest']
    STATS_KEYWORDS = ['win rate', 'wr', 'gih', 'drawn', 'pick number', 'statistics', 'stats']
    PICK_SPECIFIC_KEYWORDS = ['pick', 'pack', 'at pick', 'pick #', 'pack #', 'first pick', 'last pick']
    DECK_BUILDING_KEYWORDS = ['build', 'deck', 'construct', 'make a deck', 'deck list']
    DRAFT_DIRECTION_KEYWORDS = ['direction', 'what direction', 'what colors', 'which colors', 'commit']
    ARCHETYPE_EXPLANATION_KEYWORDS = ['what does', 'how does', 'explain', 'describe', 'archetype']
    FOLLOW_UP_KEYWORDS = ['tell me more', 'more about', 'what about', 'also', 'and']
    ELABORATION_KEYWORDS = ['why', 'how', 'explain', 'elaborate', 'clarify']
    
    def __init__(self, db_path: str = "mtg_draft_coach.db", enable_context: bool = True):
        """Initialize query processor."""
        self.db_path = Path(db_path)
        self.enable_context = enable_context
        self.context = ConversationContext() if enable_context else None
        self.card_cache: Dict[str, List[str]] = {}
        self._load_card_names()
    
    def _load_card_names(self):
        """Load all card names from database."""
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
            print(f"Warning: Could not load card names: {e}")
    
    # ========================================================================
    # QUERY NORMALIZATION & EXPANSION
    # ========================================================================
    
    def normalize_query(self, query: str) -> str:
        """Normalize query text."""
        normalized = query.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def expand_abbreviations(self, query: str) -> str:
        """Expand MTG abbreviations."""
        expanded = query.lower()
        sorted_abbrevs = sorted(self.ABBREVIATIONS.items(), key=lambda x: len(x[0]), reverse=True)
        for abbrev, expansion in sorted_abbrevs:
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            expanded = re.sub(pattern, expansion, expanded, flags=re.IGNORECASE)
        return expanded
    
    def rewrite_query(self, query: str) -> str:
        """Rewrite query for better AI understanding."""
        rewritten = query
        patterns = [
            (r'^(.+?)\s+good\??$', r'What is the win rate of \1?'),
            (r'^(.+?)\s+bad\??$', r'What is the win rate of \1?'),
            (r'^(.+?)\s+vs\s+(.+?)$', r'Compare the win rates of \1 and \2'),
        ]
        for pattern, replacement in patterns:
            rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
        return rewritten
    
    # ========================================================================
    # ENTITY EXTRACTION
    # ========================================================================
    
    def extract_set_codes(self, query: str) -> List[str]:
        """Extract set codes."""
        found_sets = []
        set_pattern = r'\b([A-Z]{3}|[a-z]{3})\b'
        matches = re.findall(set_pattern, query)
        for match in matches:
            set_code = match.upper()
            if set_code.lower() in self.SET_CODES:
                if set_code not in found_sets:
                    found_sets.append(set_code)
        return found_sets
    
    def extract_archetypes(self, query: str) -> List[str]:
        """Extract color combinations."""
        found_archetypes = []
        query_lower = query.lower()
        color_map = {'white': 'w', 'blue': 'u', 'black': 'b', 'red': 'r', 'green': 'g'}
        patterns = [
            r'\b([wubrg]{2,5})\b',
            r'\b([wubrg]/[wubrg])\b',
            r'(white|blue|black|red|green)\s+(white|blue|black|red|green)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                if isinstance(match, tuple):
                    archetype = ''.join(sorted([color_map.get(c.lower(), c.lower()) for c in match if c.lower() in color_map]))
                else:
                    archetype = match.replace('/', '').upper()
                if archetype and len(archetype) >= 2:
                    color_order = {'W': 0, 'U': 1, 'B': 2, 'R': 3, 'G': 4}
                    archetype = ''.join(sorted(archetype.upper(), key=lambda c: color_order.get(c, 99)))
                    if archetype not in found_archetypes:
                        found_archetypes.append(archetype)
        return found_archetypes
    
    def extract_card_names(self, query: str, set_code: Optional[str] = None) -> List[str]:
        """Extract card names from query."""
        found_cards = []
        query_lower = query.lower()
        cards_to_search = []
        if set_code and set_code in self.card_cache:
            cards_to_search = self.card_cache[set_code]
        else:
            for set_cards in self.card_cache.values():
                cards_to_search.extend(set_cards)
        cards_to_search = list(set(cards_to_search))
        query_words = set(query_lower.split())
        for card_name in cards_to_search:
            card_words = set(card_name.split())
            significant_words = [w for w in card_words if len(w) > 2]
            if significant_words:
                matches = sum(1 for word in significant_words if word in query_words)
                if matches >= len(significant_words) * 0.7:
                    if card_name not in found_cards:
                        found_cards.append(card_name)
        return found_cards
    
    def extract_pick_numbers(self, query: str) -> List[int]:
        """Extract pick numbers (0-14)."""
        found_picks = []
        patterns = [
            r'pick\s*(?:number|#)?\s*(\d+)',
            r'(\d+)(?:st|nd|rd|th)?\s*pick',
            r'at\s*pick\s*(\d+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                try:
                    pick_num = int(match)
                    if 0 <= pick_num <= 14 and pick_num not in found_picks:
                        found_picks.append(pick_num)
                except ValueError:
                    pass
        return sorted(found_picks)
    
    def extract_pack_numbers(self, query: str) -> List[int]:
        """Extract pack numbers (0-2)."""
        found_packs = []
        patterns = [
            r'pack\s*(?:number|#)?\s*(\d+)',
            r'(\d+)(?:st|nd|rd|th)?\s*pack',
            r'in\s*pack\s*(\d+)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                try:
                    pack_num = int(match) - 1
                    if 0 <= pack_num <= 2 and pack_num not in found_packs:
                        found_packs.append(pack_num)
                except ValueError:
                    pass
        return sorted(found_packs)
    
    def extract_metrics(self, query: str) -> List[str]:
        """Extract metric mentions."""
        found_metrics = []
        query_lower = query.lower()
        metric_keywords = {
            'win rate': 'win_rate', 'wr': 'win_rate', 'gih wr': 'gih_wr',
            'drawn wr': 'drawn_wr', 'pick number': 'pick_number', 'cmc': 'cmc',
        }
        for keyword, metric in metric_keywords.items():
            if keyword in query_lower and metric not in found_metrics:
                found_metrics.append(metric)
        return found_metrics
    
    # ========================================================================
    # INTENT CLASSIFICATION
    # ========================================================================
    
    def detect_follow_up(self, query: str) -> Tuple[bool, List[str]]:
        """Detect if query is a follow-up."""
        query_lower = query.lower().strip()
        is_follow_up = any(keyword in query_lower for keyword in self.FOLLOW_UP_KEYWORDS + self.ELABORATION_KEYWORDS)
        return is_follow_up, []
    
    def classify_intent(self, query: str, entities: ExtractedEntities, is_follow_up: bool) -> QueryIntent:
        """Classify query intent."""
        query_lower = query.lower()
        if is_follow_up:
            if any(keyword in query_lower for keyword in self.ELABORATION_KEYWORDS):
                return QueryIntent.ELABORATION
            return QueryIntent.FOLLOW_UP
        if entities.pick_numbers or entities.pack_numbers:
            if any(keyword in query_lower for keyword in self.PICK_SPECIFIC_KEYWORDS):
                return QueryIntent.PICK_SPECIFIC
        if any(keyword in query_lower for keyword in self.DECK_BUILDING_KEYWORDS):
            return QueryIntent.DECK_BUILDING
        if any(keyword in query_lower for keyword in self.DRAFT_DIRECTION_KEYWORDS):
            return QueryIntent.DRAFT_DIRECTION
        if entities.archetypes and any(keyword in query_lower for keyword in self.ARCHETYPE_EXPLANATION_KEYWORDS):
            return QueryIntent.ARCHETYPE_EXPLANATION
        if any(keyword in query_lower for keyword in self.COMPARISON_KEYWORDS):
            if len(entities.cards) >= 2:
                return QueryIntent.CARD_COMPARISON
        if any(keyword in query_lower for keyword in self.STATS_KEYWORDS):
            return QueryIntent.STATISTICS_QUERY
        if entities.archetypes:
            return QueryIntent.ARCHETYPE_QUERY
        if len(entities.cards) == 1:
            return QueryIntent.CARD_EVALUATION
        if len(entities.cards) > 1:
            return QueryIntent.CARD_COMPARISON
        return QueryIntent.GENERAL
    
    def determine_query_type(self, intent: QueryIntent) -> QueryType:
        """Determine query type."""
        mapping = {
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
        }
        return mapping.get(intent, QueryType.GENERAL)
    
    # ========================================================================
    # ANALYSIS & ENRICHMENT
    # ========================================================================
    
    def analyze_complexity(self, query: str, entities: ExtractedEntities, intent: QueryIntent) -> QueryComplexity:
        """Analyze query complexity."""
        score = 0
        entity_count = len(entities.cards) + len(entities.archetypes) + len(entities.set_codes)
        if entity_count == 0:
            score += 1
        elif entity_count > 3:
            score += 2
        if 'compare' in query.lower() or 'vs' in query.lower():
            score += 2
        if intent.name in ['DRAFT_DIRECTION', 'DECK_BUILDING', 'ARCHETYPE_EXPLANATION']:
            score += 1
        if score == 0:
            return QueryComplexity.SIMPLE
        elif score <= 2:
            return QueryComplexity.MODERATE
        elif score <= 4:
            return QueryComplexity.COMPLEX
        return QueryComplexity.VERY_COMPLEX
    
    def detect_ambiguity(self, query: str, entities: ExtractedEntities) -> Tuple[AmbiguityType, List[str]]:
        """Detect ambiguities."""
        ambiguities = []
        ambiguity_type = AmbiguityType.NONE
        if len(entities.cards) > 1 and 'compare' not in query.lower():
            ambiguities.append(f"Multiple cards: {entities.cards}")
            ambiguity_type = AmbiguityType.CARD_NAME
        ambiguous_pronouns = ['it', 'that', 'this', 'they']
        if any(pronoun in query.lower() for pronoun in ambiguous_pronouns) and not entities.cards:
            ambiguities.append("Ambiguous pronoun reference")
            ambiguity_type = AmbiguityType.INTENT
        return ambiguity_type, ambiguities
    
    def validate_entities(self, entities: ExtractedEntities) -> List[str]:
        """Validate entities."""
        errors = []
        for card in entities.cards:
            found = any(card in cards for cards in self.card_cache.values())
            if not found:
                errors.append(f"Card '{card}' not found in database")
        for pick in entities.pick_numbers:
            if not (0 <= pick <= 14):
                errors.append(f"Invalid pick number: {pick}")
        return errors
    
    def generate_ai_hints(self, intent: QueryIntent, query_type: QueryType, entities: ExtractedEntities, complexity: QueryComplexity) -> Dict:
        """Generate AI hints."""
        return {
            'intent': intent.value,
            'query_type': query_type.value,
            'complexity': complexity.value,
            'entities_present': {
                'has_cards': len(entities.cards) > 0,
                'has_archetypes': len(entities.archetypes) > 0,
                'has_sets': len(entities.set_codes) > 0,
                'has_picks': len(entities.pick_numbers) > 0,
            },
            'suggested_focus': ['card_statistics'] if intent == QueryIntent.CARD_EVALUATION else ['color_archetypes'],
        }
    
    def generate_retrieval_hints(self, entities: ExtractedEntities, complexity: QueryComplexity) -> Dict:
        """Generate retrieval hints."""
        return {
            'primary_entities': {
                'cards': entities.cards[:3],
                'archetypes': entities.archetypes,
                'sets': entities.set_codes,
            },
            'filters': {
                'set': entities.set_codes[0] if entities.set_codes else None,
                'archetype': entities.archetypes[0] if entities.archetypes else None,
            },
            'expected_result_count': 3 if complexity == QueryComplexity.SIMPLE else 5,
        }
    
    # ========================================================================
    # MAIN PROCESSING
    # ========================================================================
    
    def process(self, query: str, use_context: bool = True) -> ProcessedQuery:
        """Process a query completely."""
        try:
            # Normalize and expand
            normalized = self.normalize_query(query)
            expanded = self.expand_abbreviations(normalized)
            rewritten = self.rewrite_query(expanded)
            
            # Detect follow-up
            is_follow_up, context_refs = self.detect_follow_up(query)
            
            # Extract entities
            entities = ExtractedEntities()
            entities.set_codes = self.extract_set_codes(query)
            entities.archetypes = self.extract_archetypes(query)
            entities.cards = self.extract_card_names(query, entities.set_codes[0] if entities.set_codes else None)
            entities.metrics = self.extract_metrics(query)
            entities.pick_numbers = self.extract_pick_numbers(query)
            entities.pack_numbers = self.extract_pack_numbers(query)
            
            # Merge with context if follow-up
            if is_follow_up and use_context and self.context and self.context.previous_queries:
                prev_entities = self.context.get_recent_entities()
                if not entities.cards and prev_entities.cards:
                    entities.cards = prev_entities.cards[:]
                if not entities.set_codes and prev_entities.set_codes:
                    entities.set_codes = prev_entities.set_codes[:]
            
            # Classify intent
            intent = self.classify_intent(query, entities, is_follow_up)
            query_type = self.determine_query_type(intent)
            
            # Analyze
            complexity = self.analyze_complexity(query, entities, intent)
            ambiguity, ambiguity_details = self.detect_ambiguity(query, entities)
            validation_errors = self.validate_entities(entities)
            
            # Generate hints
            ai_hints = self.generate_ai_hints(intent, query_type, entities, complexity)
            retrieval_hints = self.generate_retrieval_hints(entities, complexity)
            
            # Calculate confidence
            confidence = 0.5
            if entities.cards:
                confidence += 0.2
            if entities.archetypes:
                confidence += 0.15
            if intent != QueryIntent.GENERAL:
                confidence += 0.15
            confidence = min(confidence, 1.0)
            
            # Create processed query
            processed = ProcessedQuery(
                original_query=query,
                normalized_query=normalized,
                expanded_query=expanded,
                rewritten_query=rewritten,
                intent=intent,
                query_type=query_type,
                entities=entities,
                confidence=confidence,
                is_follow_up=is_follow_up,
                context_references=context_refs,
                complexity=complexity,
                ambiguity=ambiguity,
                ambiguity_details=ambiguity_details,
                requires_clarification=ambiguity != AmbiguityType.NONE or len(validation_errors) > 0,
                clarification_questions=ambiguity_details if ambiguity != AmbiguityType.NONE else [],
                ai_hints=ai_hints,
                retrieval_hints=retrieval_hints,
                validation_errors=validation_errors,
            )
            
            # Add to context
            if use_context and self.context:
                self.context.add_query(processed)
            
            return processed
            
        except Exception as e:
            print(f"Warning: Error processing query: {e}")
            return ProcessedQuery(
                original_query=query,
                normalized_query=query.lower().strip(),
                expanded_query=query.lower().strip(),
                rewritten_query=query.lower().strip(),
                intent=QueryIntent.GENERAL,
                query_type=QueryType.GENERAL,
                entities=ExtractedEntities(),
                confidence=0.1
            )


# ============================================================================
# INTERFACE
# ============================================================================

class MTGDraftQueryProcessorInterface:
    """High-level interface for processing queries."""
    
    def __init__(self, db_path: str = "mtg_draft_coach.db", input_handler: Optional[InputHandler] = None, enable_context: bool = True):
        self.processor = MTGDraftQueryProcessor(db_path, enable_context=enable_context)
        self.input_handler = input_handler or TerminalInputHandler()
    
    def set_input_handler(self, handler: InputHandler):
        """Set input handler."""
        self.input_handler = handler
    
    def clear_context(self):
        """Clear conversation context."""
        if self.processor.context:
            self.processor.context.clear()
    
    def process_queries(self) -> List[ProcessedQuery]:
        """Process queries from input source."""
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
        """Process a single query."""
        return self.processor.process(query)
    
    def _print_processed_query(self, processed: ProcessedQuery):
        """Print processed query information."""
        print(f"  Intent: {processed.intent.value}")
        print(f"  Type: {processed.query_type.value}")
        print(f"  Complexity: {processed.complexity.value}")
        print(f"  Confidence: {processed.confidence:.2f}")
        print(f"  Entities: {processed.entities}")
        if processed.requires_clarification:
            print(f"  ⚠️  Requires Clarification: {processed.clarification_questions}")
        if processed.validation_errors:
            print(f"  ⚠️  Validation Errors: {processed.validation_errors}")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="MTG Draft Coach Query Processor")
    parser.add_argument('--db', default='mtg_draft_coach.db', help='Database path')
    parser.add_argument('--query', help='Process single query')
    parser.add_argument('--file', help='Process queries from file')
    args = parser.parse_args()
    
    if args.query:
        processor = MTGDraftQueryProcessor(args.db)
        processed = processor.process(args.query)
        print("\n" + "=" * 80)
        print("PROCESSED QUERY")
        print("=" * 80)
        print(f"Original: {processed.original_query}")
        print(f"Expanded: {processed.expanded_query}")
        print(f"Rewritten: {processed.rewritten_query}")
        print(f"Intent: {processed.intent.value}")
        print(f"Type: {processed.query_type.value}")
        print(f"Complexity: {processed.complexity.value}")
        print(f"Confidence: {processed.confidence:.2f}")
        print(f"Entities: {processed.entities}")
        print(f"AI Hints: {processed.ai_hints}")
        print(f"Retrieval Hints: {processed.retrieval_hints}")
    elif args.file:
        handler = FileInputHandler(args.file)
        interface = MTGDraftQueryProcessorInterface(args.db, handler)
        interface.process_queries()
    else:
        interface = MTGDraftQueryProcessorInterface(args.db)
        interface.process_queries()


if __name__ == "__main__":
    main()

