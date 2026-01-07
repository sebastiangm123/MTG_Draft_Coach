#!/usr/bin/env python3
"""
Knowledge Base Extractor for MTG Draft Coach RAG System

Part 2 of RAG Components Plan:
- Query SQLite database based on processed query
- Extract relevant context chunks
- Format data for embedding

Uses the Query Processor (Part 1) to understand query intent and entities.
"""

import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from rag.mtg_draft_query_processor import (
    ProcessedQuery,
    QueryIntent,
    QueryType,
    ExtractedEntities
)


@dataclass
class CardData:
    """Card data from database."""
    card_id: int
    card_name: str
    set: str
    color_identity: Optional[str]
    card_type: Optional[str]
    cmc: Optional[int]
    rarity: Optional[str]
    gih_wr: Optional[float] = None
    drawn_wr: Optional[float] = None
    overall_wr: Optional[float] = None
    avg_pick_number: Optional[float] = None
    maindeck_rate: Optional[float] = None
    gih_games: Optional[int] = None
    drawn_games: Optional[int] = None
    total_games: Optional[int] = None


@dataclass
class ArchetypeData:
    """Archetype data from database."""
    archetype_id: int
    main_colors: str
    splash_colors: Optional[str]
    full_color_identity: str
    set: str
    event_type: Optional[str]
    win_rate: Optional[float]
    total_games: Optional[int]
    total_wins: Optional[int]
    avg_num_turns: Optional[float]


@dataclass
class DraftPatternData:
    """Draft pattern data."""
    set: str
    event_type: Optional[str]
    pack_number: Optional[int]
    pick_number: Optional[int]
    card_id: Optional[int]
    card_name: Optional[str]
    avg_maindeck_rate: Optional[float]
    count: int


@dataclass
class ExtractedContext:
    """Context extracted from knowledge base."""
    cards: List[CardData] = field(default_factory=list)
    archetypes: List[ArchetypeData] = field(default_factory=list)
    draft_patterns: List[DraftPatternData] = field(default_factory=list)
    total_chunks: int = 0
    
    def __str__(self):
        return f"ExtractedContext: {len(self.cards)} cards, {len(self.archetypes)} archetypes, {len(self.draft_patterns)} patterns"


def _safe_get(row, key, default=None):
    """Safely get value from sqlite3.Row."""
    try:
        return row[key] if key in row.keys() else default
    except (KeyError, TypeError):
        return default


class KnowledgeBaseExtractor:
    """
    Extracts relevant context from SQLite database based on processed queries.
    """
    
    def __init__(self, db_path: str = "mtg_draft_coach.db"):
        """Initialize extractor with database path."""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def extract(self, processed_query: ProcessedQuery, max_results: int = 10) -> ExtractedContext:
        """
        Extract relevant context based on processed query.
        
        Args:
            processed_query: Processed query from Query Processor
            max_results: Maximum number of results per type
            
        Returns:
            ExtractedContext with relevant data
        """
        context = ExtractedContext()
        
        # Extract based on intent and entities
        intent = processed_query.intent
        entities = processed_query.entities
        query_type = processed_query.query_type
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Extract cards if present or if card-related intent
                if entities.cards or intent in [
                    QueryIntent.CARD_EVALUATION,
                    QueryIntent.CARD_COMPARISON,
                    QueryIntent.STATISTICS_QUERY,
                    QueryIntent.PICK_SPECIFIC,
                    QueryIntent.PICK_ADVICE
                ]:
                    context.cards = self._extract_cards(
                        cursor, entities, intent, max_results
                    )
                
                # Extract archetypes if present or if archetype-related intent
                if entities.archetypes or intent in [
                    QueryIntent.ARCHETYPE_QUERY,
                    QueryIntent.ARCHETYPE_EXPLANATION,
                    QueryIntent.DECK_BUILDING,
                    QueryIntent.DRAFT_DIRECTION
                ]:
                    context.archetypes = self._extract_archetypes(
                        cursor, entities, intent, max_results
                    )
                
                # Extract draft patterns for pick-specific queries
                if intent == QueryIntent.PICK_SPECIFIC or entities.pick_numbers or entities.pack_numbers:
                    context.draft_patterns = self._extract_draft_patterns(
                        cursor, entities, max_results
                    )
                
                # If no specific entities, extract general context
                if not context.cards and not context.archetypes and not context.draft_patterns:
                    context.cards = self._extract_general_cards(cursor, entities, max_results)
                    context.archetypes = self._extract_general_archetypes(cursor, entities, max_results)
                
                context.total_chunks = len(context.cards) + len(context.archetypes) + len(context.draft_patterns)
        
        except Exception as e:
            print(f"Error extracting context: {e}")
            import traceback
            traceback.print_exc()
        
        return context
    
    def _extract_cards(
        self,
        cursor: sqlite3.Cursor,
        entities: ExtractedEntities,
        intent: QueryIntent,
        max_results: int
    ) -> List[CardData]:
        """Extract card data based on entities and intent."""
        cards = []
        
        # Build query based on entities
        query_parts = []
        params = []
        
        # Filter by card names
        if entities.cards:
            placeholders = ','.join(['?' for _ in entities.cards])
            query_parts.append(f"c.card_name IN ({placeholders})")
            params.extend([card.lower() for card in entities.cards])
        
        # Filter by set
        if entities.set_codes:
            placeholders = ','.join(['?' for _ in entities.set_codes])
            query_parts.append(f'c."set" IN ({placeholders})')
            params.extend([s.upper() for s in entities.set_codes])
        
        # Filter by color identity (from archetypes)
        if entities.archetypes:
            color_filters = []
            for arch in entities.archetypes:
                if arch:
                    color_filters.append(f"c.color_identity LIKE '%{arch[0]}%'")
                    if len(arch) > 1:
                        color_filters.append(f"c.color_identity LIKE '%{arch[1]}%'")
            if color_filters:
                query_parts.append(f"({' OR '.join(color_filters)})")
        
        # Build WHERE clause
        where_clause = " AND ".join(query_parts) if query_parts else "1=1"
        
        # Order by relevance (win rate for statistics queries, pick number for pick queries)
        order_by = "cs.overall_wr DESC"
        if intent == QueryIntent.PICK_SPECIFIC:
            order_by = "cs.avg_pick_number ASC, cs.overall_wr DESC"
        elif intent == QueryIntent.STATISTICS_QUERY:
            order_by = "cs.gih_wr DESC"
        
        sql = f"""
            SELECT 
                c.card_id,
                c.card_name,
                c."set",
                c.color_identity,
                c.card_type,
                c.cmc,
                c.rarity,
                cs.gih_wr,
                cs.drawn_wr,
                cs.overall_wr,
                cs.avg_pick_number,
                cs.maindeck_rate,
                cs.gih_games,
                cs.drawn_games,
                cs.total_games
            FROM cards c
            LEFT JOIN card_statistics cs ON c.card_id = cs.card_id AND c."set" = cs."set"
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT ?
        """
        params.append(max_results)
        
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for row in rows:
                card = CardData(
                    card_id=row['card_id'],
                    card_name=row['card_name'],
                    set=row['set'],
                    color_identity=_safe_get(row, 'color_identity'),
                    card_type=_safe_get(row, 'card_type'),
                    cmc=_safe_get(row, 'cmc'),
                    rarity=_safe_get(row, 'rarity'),
                    gih_wr=_safe_get(row, 'gih_wr'),
                    drawn_wr=_safe_get(row, 'drawn_wr'),
                    overall_wr=_safe_get(row, 'overall_wr'),
                    avg_pick_number=_safe_get(row, 'avg_pick_number'),
                    maindeck_rate=_safe_get(row, 'maindeck_rate'),
                    gih_games=_safe_get(row, 'gih_games'),
                    drawn_games=_safe_get(row, 'drawn_games'),
                    total_games=_safe_get(row, 'total_games')
                )
                cards.append(card)
        except Exception as e:
            print(f"Error extracting cards: {e}")
            print(f"SQL: {sql}")
            print(f"Params: {params}")
        
        return cards
    
    def _extract_archetypes(
        self,
        cursor: sqlite3.Cursor,
        entities: ExtractedEntities,
        intent: QueryIntent,
        max_results: int
    ) -> List[ArchetypeData]:
        """Extract archetype data based on entities and intent."""
        archetypes = []
        
        query_parts = []
        params = []
        
        # Filter by archetype colors
        if entities.archetypes:
            color_filters = []
            for arch in entities.archetypes:
                if arch:
                    # Match main_colors or full_color_identity
                    color_filters.append("ca.main_colors = ?")
                    params.append(arch.upper())
            if color_filters:
                query_parts.append(f"({' OR '.join(color_filters)})")
        
        # Filter by set
        if entities.set_codes:
            placeholders = ','.join(['?' for _ in entities.set_codes])
            query_parts.append(f'ca."set" IN ({placeholders})')
            params.extend([s.upper() for s in entities.set_codes])
        
        where_clause = " AND ".join(query_parts) if query_parts else "1=1"
        
        sql = f"""
            SELECT 
                ca.archetype_id,
                ca.main_colors,
                ca.splash_colors,
                ca.full_color_identity,
                ca."set",
                ca.event_type,
                ca.win_rate,
                ca.total_games,
                ca.total_wins,
                ca.avg_num_turns
            FROM color_archetypes ca
            WHERE {where_clause}
            ORDER BY ca.win_rate DESC, ca.total_games DESC
            LIMIT ?
        """
        params.append(max_results)
        
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for row in rows:
                archetype = ArchetypeData(
                    archetype_id=row['archetype_id'],
                    main_colors=row['main_colors'],
                    splash_colors=_safe_get(row, 'splash_colors'),
                    full_color_identity=_safe_get(row, 'full_color_identity'),
                    set=row['set'],
                    event_type=_safe_get(row, 'event_type'),
                    win_rate=_safe_get(row, 'win_rate'),
                    total_games=_safe_get(row, 'total_games'),
                    total_wins=_safe_get(row, 'total_wins'),
                    avg_num_turns=_safe_get(row, 'avg_num_turns')
                )
                archetypes.append(archetype)
        except Exception as e:
            print(f"Error extracting archetypes: {e}")
            print(f"SQL: {sql}")
            print(f"Params: {params}")
        
        return archetypes
    
    def _extract_draft_patterns(
        self,
        cursor: sqlite3.Cursor,
        entities: ExtractedEntities,
        max_results: int
    ) -> List[DraftPatternData]:
        """Extract draft pattern data for pick-specific queries."""
        patterns = []
        
        query_parts = []
        params = []
        
        # Filter by pack number
        if entities.pack_numbers:
            placeholders = ','.join(['?' for _ in entities.pack_numbers])
            query_parts.append(f"dp.pack_number IN ({placeholders})")
            params.extend(entities.pack_numbers)
        
        # Filter by pick number
        if entities.pick_numbers:
            placeholders = ','.join(['?' for _ in entities.pick_numbers])
            query_parts.append(f"dp.pick_number IN ({placeholders})")
            params.extend(entities.pick_numbers)
        
        # Filter by set
        if entities.set_codes:
            placeholders = ','.join(['?' for _ in entities.set_codes])
            query_parts.append(f'dp."set" IN ({placeholders})')
            params.extend([s.upper() for s in entities.set_codes])
        
        where_clause = " AND ".join(query_parts) if query_parts else "1=1"
        
        sql = f"""
            SELECT 
                dp."set",
                dp.event_type,
                dp.pack_number,
                dp.pick_number,
                dp.card_id,
                c.card_name,
                AVG(dp.maindeck_rate) as avg_maindeck_rate,
                COUNT(*) as count
            FROM draft_picks dp
            LEFT JOIN cards c ON dp.card_id = c.card_id
            WHERE {where_clause}
            GROUP BY dp."set", dp.event_type, dp.pack_number, dp.pick_number, dp.card_id, c.card_name
            ORDER BY count DESC, avg_maindeck_rate DESC
            LIMIT ?
        """
        params.append(max_results)
        
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for row in rows:
                pattern = DraftPatternData(
                    set=row['set'],
                    event_type=row['event_type'],
                    pack_number=row['pack_number'],
                    pick_number=row['pick_number'],
                    card_id=row['card_id'],
                    card_name=row['card_name'],
                    avg_maindeck_rate=row['avg_maindeck_rate'],
                    count=row['count']
                )
                patterns.append(pattern)
        except Exception as e:
            print(f"Error extracting draft patterns: {e}")
            print(f"SQL: {sql}")
            print(f"Params: {params}")
        
        return patterns
    
    def _extract_general_cards(
        self,
        cursor: sqlite3.Cursor,
        entities: ExtractedEntities,
        max_results: int
    ) -> List[CardData]:
        """Extract general cards when no specific entities."""
        query_parts = []
        params = []
        
        if entities.set_codes:
            placeholders = ','.join(['?' for _ in entities.set_codes])
            query_parts.append(f'c."set" IN ({placeholders})')
            params.extend([s.upper() for s in entities.set_codes])
        
        where_clause = " AND ".join(query_parts) if query_parts else "1=1"
        
        sql = f"""
            SELECT 
                c.card_id,
                c.card_name,
                c."set",
                c.color_identity,
                c.card_type,
                c.cmc,
                c.rarity,
                cs.gih_wr,
                cs.drawn_wr,
                cs.overall_wr,
                cs.avg_pick_number,
                cs.maindeck_rate,
                cs.gih_games,
                cs.drawn_games,
                cs.total_games
            FROM cards c
            LEFT JOIN card_statistics cs ON c.card_id = cs.card_id AND c."set" = cs."set"
            WHERE {where_clause} AND cs.overall_wr IS NOT NULL
            ORDER BY cs.overall_wr DESC
            LIMIT ?
        """
        params.append(max_results)
        
        cards = []
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for row in rows:
                card = CardData(
                    card_id=row['card_id'],
                    card_name=row['card_name'],
                    set=row['set'],
                    color_identity=_safe_get(row, 'color_identity'),
                    card_type=_safe_get(row, 'card_type'),
                    cmc=_safe_get(row, 'cmc'),
                    rarity=_safe_get(row, 'rarity'),
                    gih_wr=_safe_get(row, 'gih_wr'),
                    drawn_wr=_safe_get(row, 'drawn_wr'),
                    overall_wr=_safe_get(row, 'overall_wr'),
                    avg_pick_number=_safe_get(row, 'avg_pick_number'),
                    maindeck_rate=_safe_get(row, 'maindeck_rate'),
                    gih_games=_safe_get(row, 'gih_games'),
                    drawn_games=_safe_get(row, 'drawn_games'),
                    total_games=_safe_get(row, 'total_games')
                )
                cards.append(card)
        except Exception as e:
            print(f"Error extracting general cards: {e}")
        
        return cards
    
    def _extract_general_archetypes(
        self,
        cursor: sqlite3.Cursor,
        entities: ExtractedEntities,
        max_results: int
    ) -> List[ArchetypeData]:
        """Extract general archetypes when no specific entities."""
        query_parts = []
        params = []
        
        if entities.set_codes:
            placeholders = ','.join(['?' for _ in entities.set_codes])
            query_parts.append(f'ca."set" IN ({placeholders})')
            params.extend([s.upper() for s in entities.set_codes])
        
        where_clause = " AND ".join(query_parts) if query_parts else "1=1"
        
        sql = f"""
            SELECT 
                ca.archetype_id,
                ca.main_colors,
                ca.splash_colors,
                ca.full_color_identity,
                ca."set",
                ca.event_type,
                ca.win_rate,
                ca.total_games,
                ca.total_wins,
                ca.avg_num_turns
            FROM color_archetypes ca
            WHERE {where_clause}
            ORDER BY ca.win_rate DESC, ca.total_games DESC
            LIMIT ?
        """
        params.append(max_results)
        
        archetypes = []
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for row in rows:
                archetype = ArchetypeData(
                    archetype_id=row['archetype_id'],
                    main_colors=row['main_colors'],
                    splash_colors=_safe_get(row, 'splash_colors'),
                    full_color_identity=_safe_get(row, 'full_color_identity'),
                    set=row['set'],
                    event_type=_safe_get(row, 'event_type'),
                    win_rate=_safe_get(row, 'win_rate'),
                    total_games=_safe_get(row, 'total_games'),
                    total_wins=_safe_get(row, 'total_wins'),
                    avg_num_turns=_safe_get(row, 'avg_num_turns')
                )
                archetypes.append(archetype)
        except Exception as e:
            print(f"Error extracting general archetypes: {e}")
        
        return archetypes

