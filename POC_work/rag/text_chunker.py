#!/usr/bin/env python3
"""
Text Chunker / Document Preparer for MTG Draft Coach RAG System

Part 3 of RAG Components Plan:
- Split data into semantic chunks
- Create structured text representations
- Add metadata (card_id, set, type, etc.)

Converts database records into text chunks suitable for embedding.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from rag.knowledge_base_extractor import (
    CardData,
    ArchetypeData,
    DraftPatternData,
    ExtractedContext
)


class ChunkType(Enum):
    """Types of chunks."""
    CARD = "card"
    ARCHETYPE = "archetype"
    DRAFT_PATTERN = "draft_pattern"
    COMPARISON = "comparison"


@dataclass
class TextChunk:
    """A text chunk ready for embedding."""
    chunk_id: str
    chunk_type: ChunkType
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __str__(self):
        return f"TextChunk({self.chunk_type.value}, id={self.chunk_id}, text_length={len(self.text)})"


class TextChunker:
    """
    Converts extracted context into structured text chunks.
    """
    
    def __init__(self):
        """Initialize chunker."""
        pass
    
    def chunk_context(self, context: ExtractedContext) -> List[TextChunk]:
        """
        Convert extracted context into text chunks.
        
        Args:
            context: ExtractedContext from Knowledge Base Extractor
            
        Returns:
            List of TextChunk objects
        """
        chunks = []
        
        # Chunk cards
        for card in context.cards:
            chunk = self._chunk_card(card)
            if chunk:
                chunks.append(chunk)
        
        # Chunk archetypes
        for archetype in context.archetypes:
            chunk = self._chunk_archetype(archetype)
            if chunk:
                chunks.append(chunk)
        
        # Chunk draft patterns
        for pattern in context.draft_patterns:
            chunk = self._chunk_draft_pattern(pattern)
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _chunk_card(self, card: CardData) -> Optional[TextChunk]:
        """Convert card data into text chunk."""
        if not card.card_name:
            return None
        
        # Build text representation
        lines = []
        lines.append(f"Card: {card.card_name.title()}")
        
        if card.set:
            lines.append(f"Set: {card.set}")
        
        if card.card_type:
            lines.append(f"Type: {card.card_type}")
        
        # Card properties
        props = []
        if card.cmc is not None:
            props.append(f"CMC: {card.cmc}")
        if card.color_identity:
            colors = self._format_colors(card.color_identity)
            props.append(f"Colors: {colors}")
        if card.rarity:
            props.append(f"Rarity: {card.rarity.title()}")
        if props:
            lines.append(", ".join(props))
        
        # Statistics section
        lines.append("")
        lines.append("Performance Statistics:")
        
        if card.gih_wr is not None:
            gih_pct = card.gih_wr * 100
            games_str = f" ({card.gih_games:,} games)" if card.gih_games else ""
            lines.append(f"  Opening Hand Win Rate: {gih_pct:.2f}%{games_str}")
        
        if card.drawn_wr is not None:
            drawn_pct = card.drawn_wr * 100
            games_str = f" ({card.drawn_games:,} games)" if card.drawn_games else ""
            lines.append(f"  Drawn Win Rate: {drawn_pct:.2f}%{games_str}")
        
        if card.overall_wr is not None:
            overall_pct = card.overall_wr * 100
            games_str = f" ({card.total_games:,} games)" if card.total_games else ""
            lines.append(f"  Overall Win Rate: {overall_pct:.2f}%{games_str}")
        
        if card.avg_pick_number is not None:
            lines.append(f"  Average Pick Number: {card.avg_pick_number:.2f}")
        
        if card.maindeck_rate is not None:
            maindeck_pct = card.maindeck_rate * 100
            lines.append(f"  Maindeck Rate: {maindeck_pct:.2f}%")
        
        text = "\n".join(lines)
        
        # Build metadata
        metadata = {
            "chunk_type": ChunkType.CARD.value,
            "card_id": card.card_id,
            "card_name": card.card_name.lower(),
            "set": card.set,
            "color_identity": card.color_identity or "",
            "cmc": card.cmc,
            "rarity": card.rarity or "",
            "gih_wr": card.gih_wr,
            "drawn_wr": card.drawn_wr,
            "overall_wr": card.overall_wr,
            "avg_pick_number": card.avg_pick_number,
        }
        
        chunk_id = f"card_{card.card_id}_{card.set}"
        
        return TextChunk(
            chunk_id=chunk_id,
            chunk_type=ChunkType.CARD,
            text=text,
            metadata=metadata
        )
    
    def _chunk_archetype(self, archetype: ArchetypeData) -> Optional[TextChunk]:
        """Convert archetype data into text chunk."""
        if not archetype.main_colors:
            return None
        
        # Build text representation
        lines = []
        colors_display = self._format_archetype_colors(archetype.main_colors, archetype.splash_colors)
        lines.append(f"Archetype: {colors_display}")
        
        if archetype.set:
            lines.append(f"Set: {archetype.set}")
        
        if archetype.event_type:
            lines.append(f"Event Type: {archetype.event_type}")
        
        # Statistics section
        lines.append("")
        lines.append("Performance Statistics:")
        
        if archetype.win_rate is not None:
            wr_pct = archetype.win_rate * 100
            games_str = f" ({archetype.total_games:,} games)" if archetype.total_games else ""
            lines.append(f"  Win Rate: {wr_pct:.2f}%{games_str}")
        
        if archetype.total_wins is not None and archetype.total_games is not None:
            losses = archetype.total_games - archetype.total_wins
            lines.append(f"  Record: {archetype.total_wins:,} wins, {losses:,} losses")
        
        if archetype.avg_num_turns is not None:
            lines.append(f"  Average Game Length: {archetype.avg_num_turns:.2f} turns")
        
        text = "\n".join(lines)
        
        # Build metadata
        metadata = {
            "chunk_type": ChunkType.ARCHETYPE.value,
            "archetype_id": archetype.archetype_id,
            "main_colors": archetype.main_colors,
            "splash_colors": archetype.splash_colors or "",
            "full_color_identity": archetype.full_color_identity,
            "set": archetype.set,
            "event_type": archetype.event_type or "",
            "win_rate": archetype.win_rate,
            "total_games": archetype.total_games,
        }
        
        chunk_id = f"archetype_{archetype.main_colors}_{archetype.set}"
        if archetype.event_type:
            chunk_id += f"_{archetype.event_type}"
        
        return TextChunk(
            chunk_id=chunk_id,
            chunk_type=ChunkType.ARCHETYPE,
            text=text,
            metadata=metadata
        )
    
    def _chunk_draft_pattern(self, pattern: DraftPatternData) -> Optional[TextChunk]:
        """Convert draft pattern data into text chunk."""
        if not pattern.card_name:
            return None
        
        # Build text representation
        lines = []
        pack_str = f"Pack {pattern.pack_number + 1}" if pattern.pack_number is not None else "Any Pack"
        pick_str = f"Pick {pattern.pick_number + 1}" if pattern.pick_number is not None else "Any Pick"
        lines.append(f"Draft Pattern: {pack_str}, {pick_str}")
        
        if pattern.set:
            lines.append(f"Set: {pattern.set}")
        
        if pattern.event_type:
            lines.append(f"Event Type: {pattern.event_type}")
        
        lines.append(f"Card: {pattern.card_name.title()}")
        
        # Statistics
        lines.append("")
        lines.append("Draft Statistics:")
        lines.append(f"  Times Picked: {pattern.count:,}")
        
        if pattern.avg_maindeck_rate is not None:
            maindeck_pct = pattern.avg_maindeck_rate * 100
            lines.append(f"  Average Maindeck Rate: {maindeck_pct:.2f}%")
        
        text = "\n".join(lines)
        
        # Build metadata
        metadata = {
            "chunk_type": ChunkType.DRAFT_PATTERN.value,
            "set": pattern.set,
            "event_type": pattern.event_type or "",
            "pack_number": pattern.pack_number,
            "pick_number": pattern.pick_number,
            "card_id": pattern.card_id,
            "card_name": pattern.card_name.lower() if pattern.card_name else "",
            "count": pattern.count,
            "avg_maindeck_rate": pattern.avg_maindeck_rate,
        }
        
        chunk_id = f"pattern_{pattern.set}_{pattern.pack_number}_{pattern.pick_number}_{pattern.card_id}"
        
        return TextChunk(
            chunk_id=chunk_id,
            chunk_type=ChunkType.DRAFT_PATTERN,
            text=text,
            metadata=metadata
        )
    
    def _format_colors(self, color_identity: str) -> str:
        """Format color identity string."""
        if not color_identity:
            return "Colorless"
        
        color_map = {
            'W': 'White',
            'U': 'Blue',
            'B': 'Black',
            'R': 'Red',
            'G': 'Green'
        }
        
        colors = [color_map.get(c, c) for c in color_identity.upper()]
        if len(colors) == 0:
            return "Colorless"
        elif len(colors) == 1:
            return colors[0]
        else:
            return "-".join(colors)
    
    def _format_archetype_colors(self, main_colors: str, splash_colors: Optional[str] = None) -> str:
        """Format archetype colors for display."""
        color_map = {
            'W': 'White',
            'U': 'Blue',
            'B': 'Black',
            'R': 'Red',
            'G': 'Green'
        }
        
        main = "/".join([color_map.get(c, c) for c in main_colors.upper()])
        
        if splash_colors:
            splash = "/".join([color_map.get(c, c) for c in splash_colors.upper()])
            return f"{main} (Splash: {splash})"
        
        return main
    
    def create_comparison_chunk(self, cards: List[CardData]) -> Optional[TextChunk]:
        """Create a comparison chunk for multiple cards."""
        if len(cards) < 2:
            return None
        
        lines = []
        lines.append("Card Comparison:")
        lines.append("")
        
        for card in cards:
            lines.append(f"{card.card_name.title()} ({card.set}):")
            if card.overall_wr is not None:
                wr_pct = card.overall_wr * 100
                lines.append(f"  Overall Win Rate: {wr_pct:.2f}%")
            if card.avg_pick is not None:
                lines.append(f"  Average Pick: {card.avg_pick:.2f}")
            lines.append("")
        
        text = "\n".join(lines)
        
        metadata = {
            "chunk_type": ChunkType.COMPARISON.value,
            "card_count": len(cards),
            "card_ids": [c.card_id for c in cards],
            "card_names": [c.card_name.lower() for c in cards],
        }
        
        chunk_id = f"comparison_{'_'.join([str(c.card_id) for c in cards])}"
        
        return TextChunk(
            chunk_id=chunk_id,
            chunk_type=ChunkType.COMPARISON,
            text=text,
            metadata=metadata
        )

