#!/usr/bin/env python3
"""
Query Preprocessor Enhancements for AI Model Integration

This module enhances the query processor to be a comprehensive preprocessor
that handles any draft-related question and prepares it optimally for AI models.
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import difflib


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"  # Single entity, clear intent
    MODERATE = "moderate"  # Multiple entities or moderate complexity
    COMPLEX = "complex"  # Multiple parts, comparisons, complex logic
    VERY_COMPLEX = "very_complex"  # Multi-part, requires multiple data sources


class AmbiguityType(Enum):
    """Types of ambiguity in queries."""
    NONE = "none"
    CARD_NAME = "card_name"  # Ambiguous card reference
    ARCHETYPE = "archetype"  # Ambiguous archetype
    METRIC = "metric"  # Ambiguous metric
    INTENT = "intent"  # Unclear intent
    MULTIPLE = "multiple"  # Multiple ambiguities


@dataclass
class QueryEnrichment:
    """Enriched query information for AI processing."""
    original_query: str
    normalized_query: str
    expanded_query: str  # Query with abbreviations expanded
    rewritten_query: str  # Query rewritten for AI clarity
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


class AbbreviationExpander:
    """Expands MTG and draft-related abbreviations."""
    
    # MTG abbreviations
    ABBREVIATIONS = {
        # Win rate abbreviations
        'wr': 'win rate',
        'gih': 'games in hand',
        'gih wr': 'games in hand win rate',
        'gihwr': 'games in hand win rate',
        'drawn wr': 'drawn win rate',
        'drawnwr': 'drawn win rate',
        'overall wr': 'overall win rate',
        'overallwr': 'overall win rate',
        
        # Draft abbreviations
        'p1p1': 'pack 1 pick 1',
        'p1p2': 'pack 1 pick 2',
        'p2p1': 'pack 2 pick 1',
        'p3p1': 'pack 3 pick 1',
        'p1': 'pack 1',
        'p2': 'pack 2',
        'p3': 'pack 3',
        
        # Card type abbreviations
        'cmc': 'converted mana cost',
        'mv': 'mana value',
        'ci': 'color identity',
        'ci ': 'color identity ',
        
        # Rarity abbreviations
        'c': 'common',
        'u': 'uncommon',
        'r': 'rare',
        'm': 'mythic',
        
        # Color abbreviations (context-dependent)
        'w': 'white',
        'u': 'blue',
        'b': 'black',
        'r': 'red',
        'g': 'green',
        
        # Draft terms
        'md': 'maindeck',
        'sb': 'sideboard',
        'sb ': 'sideboard ',
        'on the play': 'on the play',
        'otp': 'on the play',
        'otd': 'on the draw',
        'on the draw': 'on the draw',
        
        # Statistics
        'avg': 'average',
        'avg ': 'average ',
        'stats': 'statistics',
    }
    
    # Context-aware expansions (need surrounding context)
    CONTEXTUAL_ABBREVIATIONS = {
        'wr': {
            'after_card': 'win rate',
            'after_gih': 'win rate',
            'default': 'win rate'
        }
    }
    
    @classmethod
    def expand(cls, query: str) -> str:
        """Expand abbreviations in query."""
        expanded = query.lower()
        
        # Sort by length (longest first) to avoid partial matches
        sorted_abbrevs = sorted(cls.ABBREVIATIONS.items(), key=lambda x: len(x[0]), reverse=True)
        
        for abbrev, expansion in sorted_abbrevs:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            expanded = re.sub(pattern, expansion, expanded, flags=re.IGNORECASE)
        
        return expanded


class QueryNormalizer:
    """Normalizes queries for consistent processing."""
    
    # Common typos and variations
    TYPO_CORRECTIONS = {
        'winrate': 'win rate',
        'win-rate': 'win rate',
        'winrate ': 'win rate ',
        'picknumber': 'pick number',
        'pick-number': 'pick number',
        'packnumber': 'pack number',
        'pack-number': 'pack number',
    }
    
    # Slang and casual language
    SLANG_MAP = {
        'how good is': 'what is the win rate of',
        'how good': 'what is the performance of',
        'is good': 'what is the win rate of',
        'is bad': 'what is the win rate of',
        'sucks': 'has low win rate',
        'op': 'overpowered',
        'trash': 'has low win rate',
        'bomb': 'high win rate card',
        'drafting': 'draft',
        'drafting in': 'drafting',
    }
    
    @classmethod
    def normalize(cls, query: str) -> str:
        """Normalize query text."""
        normalized = query.lower().strip()
        
        # Fix typos
        for typo, correction in cls.TYPO_CORRECTIONS.items():
            normalized = normalized.replace(typo, correction)
        
        # Replace slang
        for slang, formal in cls.SLANG_MAP.items():
            normalized = normalized.replace(slang, formal)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Fix common punctuation issues
        normalized = normalized.replace('?', ' ?')
        normalized = normalized.replace('!', ' !')
        
        return normalized.strip()


class QueryRewriter:
    """Rewrites queries for better AI understanding."""
    
    # Query templates for common patterns
    REWRITE_PATTERNS = [
        # "X good?" -> "What is the win rate of X?"
        (r'^(.+?)\s+good\??$', r'What is the win rate of \1?'),
        
        # "X bad?" -> "What is the win rate of X?"
        (r'^(.+?)\s+bad\??$', r'What is the win rate of \1?'),
        
        # "X vs Y" -> "Compare the win rates of X and Y"
        (r'^(.+?)\s+vs\s+(.+?)$', r'Compare the win rates of \1 and \2'),
        
        # "best X" -> "What is the best X by win rate?"
        (r'best\s+(.+?)(?:\s+in\s+(.+?))?\??$', r'What is the best \1 by win rate\2?'),
        
        # "should I pick X" -> "What is the win rate of X and should I pick it?"
        (r'should i pick (.+?)\??$', r'What is the win rate of \1 and should I pick it?'),
    ]
    
    @classmethod
    def rewrite(cls, query: str) -> str:
        """Rewrite query for better AI understanding."""
        rewritten = query
        
        for pattern, replacement in cls.REWRITE_PATTERNS:
            rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
        
        return rewritten


class MultiQueryDetector:
    """Detects and splits multi-part queries."""
    
    # Patterns that indicate multiple questions
    MULTI_QUERY_INDICATORS = [
        r'\?\s+and\s+',
        r'\?\s+also\s+',
        r'\?\s+what about\s+',
        r'\.\s+what\s+',
        r'\.\s+how\s+',
        r'\.\s+why\s+',
        r',\s+and\s+what\s+',
        r',\s+also\s+',
    ]
    
    # Conjunctions that might indicate multiple parts
    CONJUNCTIONS = ['and', 'also', 'plus', 'additionally', 'furthermore']
    
    @classmethod
    def detect_and_split(cls, query: str) -> Tuple[bool, List[str]]:
        """Detect if query has multiple parts and split them."""
        is_multi = False
        sub_queries = []
        
        # Check for multiple question marks
        question_count = query.count('?')
        if question_count > 1:
            is_multi = True
            # Split by question marks
            parts = re.split(r'\?+', query)
            sub_queries = [p.strip() + '?' for p in parts if p.strip()]
        else:
            # Check for multi-query indicators
            for indicator in cls.MULTI_QUERY_INDICATORS:
                if re.search(indicator, query, re.IGNORECASE):
                    is_multi = True
                    # Try to split
                    parts = re.split(indicator, query, flags=re.IGNORECASE)
                    sub_queries = [p.strip() for p in parts if p.strip()]
                    break
        
        # If no multi-query detected, return single query
        if not is_multi:
            sub_queries = [query]
        
        return is_multi, sub_queries


class AmbiguityDetector:
    """Detects ambiguities in queries."""
    
    @classmethod
    def detect(self, query: str, entities, card_cache: Dict[str, List[str]]) -> Tuple[AmbiguityType, List[str]]:
        """Detect ambiguities in query."""
        ambiguities = []
        ambiguity_type = AmbiguityType.NONE
        
        # Check for ambiguous card references
        if len(entities.cards) > 1 and not any(keyword in query.lower() for keyword in ['compare', 'vs', 'versus']):
            ambiguities.append(f"Multiple cards mentioned: {entities.cards}")
            ambiguity_type = AmbiguityType.CARD_NAME
        
        # Check for ambiguous archetype references
        if len(entities.archetypes) > 1 and 'compare' not in query.lower():
            ambiguities.append(f"Multiple archetypes mentioned: {entities.archetypes}")
            if ambiguity_type != AmbiguityType.NONE:
                ambiguity_type = AmbiguityType.MULTIPLE
            else:
                ambiguity_type = AmbiguityType.ARCHETYPE
        
        # Check for pronouns/ambiguous references
        ambiguous_pronouns = ['it', 'that', 'this', 'they', 'them', 'those', 'these']
        query_lower = query.lower()
        for pronoun in ambiguous_pronouns:
            if pronoun in query_lower and not entities.cards and not entities.archetypes:
                ambiguities.append(f"Ambiguous reference: '{pronoun}'")
                if ambiguity_type == AmbiguityType.NONE:
                    ambiguity_type = AmbiguityType.INTENT
                else:
                    ambiguity_type = AmbiguityType.MULTIPLE
        
        # Check for vague metrics
        vague_metrics = ['good', 'bad', 'better', 'best', 'worse', 'worst']
        if any(vague in query_lower for vague in vague_metrics) and not entities.metrics:
            ambiguities.append("Vague metric reference (good/bad without specific metric)")
            if ambiguity_type == AmbiguityType.NONE:
                ambiguity_type = AmbiguityType.METRIC
        
        return ambiguity_type, ambiguities


class QueryComplexityAnalyzer:
    """Analyzes query complexity."""
    
    @classmethod
    def analyze(cls, query: str, entities, intent) -> QueryComplexity:
        """Analyze query complexity."""
        complexity_score = 0
        
        # Count entities
        entity_count = (
            len(entities.cards) +
            len(entities.archetypes) +
            len(entities.set_codes) +
            len(entities.pick_numbers) +
            len(entities.pack_numbers)
        )
        
        if entity_count == 0:
            complexity_score += 1
        elif entity_count == 1:
            complexity_score += 0
        elif entity_count <= 3:
            complexity_score += 1
        else:
            complexity_score += 2
        
        # Check for comparisons
        if 'compare' in query.lower() or 'vs' in query.lower() or 'versus' in query.lower():
            complexity_score += 2
        
        # Check for multiple conditions
        condition_words = ['if', 'when', 'where', 'unless', 'except']
        if sum(1 for word in condition_words if word in query.lower()) > 1:
            complexity_score += 1
        
        # Check for complex intent
        complex_intents = ['DRAFT_DIRECTION', 'DECK_BUILDING', 'ARCHETYPE_EXPLANATION']
        if intent.name in complex_intents:
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score == 0:
            return QueryComplexity.SIMPLE
        elif complexity_score <= 2:
            return QueryComplexity.MODERATE
        elif complexity_score <= 4:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.VERY_COMPLEX


class EntityValidator:
    """Validates extracted entities against database."""
    
    @classmethod
    def validate(cls, entities, db_path: str, card_cache: Dict[str, List[str]]) -> List[str]:
        """Validate entities and return validation errors."""
        errors = []
        
        # Validate cards exist in database
        for card in entities.cards:
            found = False
            for set_cards in card_cache.values():
                if card in set_cards:
                    found = True
                    break
            if not found:
                errors.append(f"Card '{card}' not found in database")
        
        # Validate set codes
        valid_sets = {'TLA', 'MOM', 'BRO', 'DMU', 'SNC', 'NEO', 'VOW', 'MID', 'AFR', 'STX'}
        for set_code in entities.set_codes:
            if set_code.upper() not in valid_sets:
                errors.append(f"Set code '{set_code}' may not be valid")
        
        # Validate pick numbers
        for pick in entities.pick_numbers:
            if not (0 <= pick <= 14):
                errors.append(f"Invalid pick number: {pick} (must be 0-14)")
        
        # Validate pack numbers
        for pack in entities.pack_numbers:
            if not (0 <= pack <= 2):
                errors.append(f"Invalid pack number: {pack} (must be 0-2)")
        
        return errors


class AIHintGenerator:
    """Generates hints for AI model processing."""
    
    @classmethod
    def generate(cls, processed_query, entities, complexity: QueryComplexity) -> Dict[str, any]:
        """Generate hints for AI model."""
        hints = {
            'intent': processed_query.intent.value,
            'query_type': processed_query.query_type.value,
            'complexity': complexity.value,
            'entities_present': {
                'has_cards': len(entities.cards) > 0,
                'has_archetypes': len(entities.archetypes) > 0,
                'has_sets': len(entities.set_codes) > 0,
                'has_picks': len(entities.pick_numbers) > 0,
                'has_packs': len(entities.pack_numbers) > 0,
            },
            'suggested_focus': [],
            'requires_statistics': 'statistics' in processed_query.intent.value or 'win rate' in processed_query.normalized_query,
            'requires_comparison': processed_query.intent.value == 'card_comparison',
            'requires_context': processed_query.is_follow_up,
        }
        
        # Add suggested focus based on intent
        if processed_query.intent.value == 'card_evaluation':
            hints['suggested_focus'].append('card_statistics')
            hints['suggested_focus'].append('card_metadata')
        elif processed_query.intent.value == 'archetype_query':
            hints['suggested_focus'].append('color_archetypes')
            hints['suggested_focus'].append('draft_summaries')
        elif processed_query.intent.value == 'pick_specific':
            hints['suggested_focus'].append('draft_picks')
            hints['suggested_focus'].append('card_statistics')
        
        return hints


class RetrievalHintGenerator:
    """Generates hints for RAG retrieval system."""
    
    @classmethod
    def generate(cls, processed_query, entities, complexity: QueryComplexity) -> Dict[str, any]:
        """Generate hints for retrieval system."""
        hints = {
            'primary_entities': {
                'cards': entities.cards[:3],  # Top 3 cards
                'archetypes': entities.archetypes,
                'sets': entities.set_codes,
            },
            'filters': {
                'set': entities.set_codes[0] if entities.set_codes else None,
                'archetype': entities.archetypes[0] if entities.archetypes else None,
                'pick_range': {
                    'min': min(entities.pick_numbers) if entities.pick_numbers else None,
                    'max': max(entities.pick_numbers) if entities.pick_numbers else None,
                },
                'pack_range': {
                    'min': min(entities.pack_numbers) if entities.pack_numbers else None,
                    'max': max(entities.pack_numbers) if entities.pack_numbers else None,
                },
            },
            'search_strategy': cls._determine_search_strategy(processed_query, entities),
            'expected_result_count': cls._estimate_result_count(complexity, entities),
        }
        
        return hints
    
    @classmethod
    def _determine_search_strategy(cls, processed_query, entities) -> str:
        """Determine best search strategy."""
        if processed_query.intent.value == 'card_evaluation' and entities.cards:
            return 'exact_match'
        elif processed_query.intent.value == 'archetype_query' and entities.archetypes:
            return 'archetype_filter'
        elif processed_query.intent.value == 'pick_specific':
            return 'positional_filter'
        else:
            return 'semantic_search'
    
    @classmethod
    def _estimate_result_count(cls, complexity: QueryComplexity, entities) -> int:
        """Estimate number of results needed."""
        if complexity == QueryComplexity.SIMPLE:
            return 3
        elif complexity == QueryComplexity.MODERATE:
            return 5
        elif complexity == QueryComplexity.COMPLEX:
            return 8
        else:
            return 10


class ClarificationGenerator:
    """Generates clarification questions for ambiguous queries."""
    
    @classmethod
    def generate(cls, ambiguity: AmbiguityType, ambiguity_details: List[str], entities) -> List[str]:
        """Generate clarification questions."""
        questions = []
        
        if ambiguity == AmbiguityType.CARD_NAME:
            questions.append(f"Which card are you asking about? Found: {', '.join(entities.cards)}")
        elif ambiguity == AmbiguityType.ARCHETYPE:
            questions.append(f"Which archetype are you asking about? Found: {', '.join(entities.archetypes)}")
        elif ambiguity == AmbiguityType.METRIC:
            questions.append("Which metric are you interested in? (win rate, pick number, maindeck rate, etc.)")
        elif ambiguity == AmbiguityType.INTENT:
            questions.append("Could you clarify what you'd like to know?")
        elif ambiguity == AmbiguityType.MULTIPLE:
            questions.append("I found multiple ambiguities. Could you be more specific?")
            questions.extend(ambiguity_details)
        
        return questions


class QueryPreprocessor:
    """Comprehensive query preprocessor for AI models."""
    
    def __init__(self, db_path: str = "mtg_draft_coach.db", card_cache: Optional[Dict[str, List[str]]] = None):
        """Initialize preprocessor."""
        self.db_path = db_path
        self.card_cache = card_cache or {}
    
    def preprocess(self, query: str, processed_query) -> QueryEnrichment:
        """Preprocess query for AI model."""
        # Step 1: Normalize
        normalized = QueryNormalizer.normalize(query)
        
        # Step 2: Expand abbreviations
        expanded = AbbreviationExpander.expand(normalized)
        
        # Step 3: Rewrite for clarity
        rewritten = QueryRewriter.rewrite(expanded)
        
        # Step 4: Detect multi-query
        is_multi, sub_queries = MultiQueryDetector.detect_and_split(query)
        
        # Step 5: Analyze complexity
        complexity = QueryComplexityAnalyzer.analyze(query, processed_query.entities, processed_query.intent)
        
        # Step 6: Detect ambiguity
        ambiguity, ambiguity_details = AmbiguityDetector.detect(
            query, processed_query.entities, self.card_cache
        )
        
        # Step 7: Validate entities
        validation_errors = EntityValidator.validate(
            processed_query.entities, self.db_path, self.card_cache
        )
        
        # Step 8: Generate AI hints
        ai_hints = AIHintGenerator.generate(processed_query, processed_query.entities, complexity)
        
        # Step 9: Generate retrieval hints
        retrieval_hints = RetrievalHintGenerator.generate(
            processed_query, processed_query.entities, complexity
        )
        
        # Step 10: Generate clarification questions if needed
        requires_clarification = ambiguity != AmbiguityType.NONE or len(validation_errors) > 0
        clarification_questions = []
        if requires_clarification:
            clarification_questions = ClarificationGenerator.generate(
                ambiguity, ambiguity_details, processed_query.entities
            )
        
        return QueryEnrichment(
            original_query=query,
            normalized_query=normalized,
            expanded_query=expanded,
            rewritten_query=rewritten,
            complexity=complexity,
            ambiguity=ambiguity,
            ambiguity_details=ambiguity_details,
            requires_clarification=requires_clarification,
            clarification_questions=clarification_questions,
            ai_hints=ai_hints,
            retrieval_hints=retrieval_hints,
            validation_errors=validation_errors,
            is_multi_query=is_multi,
            sub_queries=sub_queries
        )

