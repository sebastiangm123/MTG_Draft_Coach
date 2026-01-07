#!/usr/bin/env python3
"""
Retrieval System for MTG Draft Coach RAG System

Searches vector database for relevant context based on user queries.
Integrates with Query Processor to use extracted entities for filtering.
"""

from typing import List, Dict, Optional, Any
from pathlib import Path
import logging

from rag.mtg_draft_query_processor import ProcessedQuery
from rag.embedding_generator import EmbeddingGenerator
from rag.vector_database import VectorDatabase

logger = logging.getLogger(__name__)


class RetrievalSystem:
    """
    Retrieval system for finding relevant context from vector database.
    """
    
    def __init__(
        self,
        vector_db: VectorDatabase,
        embedding_generator: EmbeddingGenerator
    ):
        """
        Initialize retrieval system.
        
        Args:
            vector_db: VectorDatabase instance
            embedding_generator: EmbeddingGenerator instance
        """
        self.vector_db = vector_db
        self.embedding_generator = embedding_generator
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: User query text
            top_k: Number of results to return
            filters: Metadata filters (e.g., {"set": "TLA", "chunk_type": "card"})
            
        Returns:
            List of retrieved chunks with id, distance, document, metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embedding(query)
        
        # Search vector database
        results = self.vector_db.search(
            query_embedding=query_embedding,
            top_k=top_k,
            where=filters
        )
        
        return results
    
    def retrieve_with_query_processor(
        self,
        processed_query: ProcessedQuery,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using processed query for intelligent filtering.
        
        Args:
            processed_query: ProcessedQuery from Query Processor
            top_k: Number of results to return
            
        Returns:
            List of retrieved chunks
        """
        # Build filters from processed query
        filters = self._build_filters(processed_query)
        
        # Use rewritten query for better semantic search
        query_text = processed_query.rewritten_query or processed_query.expanded_query or processed_query.original_query
        
        # Retrieve
        results = self.retrieve(
            query=query_text,
            top_k=top_k,
            filters=filters if filters else None
        )
        
        return results
    
    def _build_filters(self, processed_query: ProcessedQuery) -> Optional[Dict[str, Any]]:
        """
        Build metadata filters from processed query.
        ChromaDB requires filters in format: {"$and": [{"key": "value"}, ...]}
        
        Args:
            processed_query: ProcessedQuery object
            
        Returns:
            Dictionary of filters in ChromaDB format or None
        """
        filter_conditions = []
        entities = processed_query.entities
        
        # Filter by set
        if entities.set_codes:
            filter_conditions.append({"set": entities.set_codes[0].upper()})
        
        # Filter by chunk type based on intent
        intent = processed_query.intent
        if intent.value in ["card_evaluation", "card_comparison", "statistics_query"]:
            filter_conditions.append({"chunk_type": "card"})
        elif intent.value in ["archetype_query", "archetype_explanation", "deck_building"]:
            filter_conditions.append({"chunk_type": "archetype"})
        elif intent.value == "pick_specific":
            filter_conditions.append({"chunk_type": "draft_pattern"})
        
        # Build ChromaDB filter format
        if len(filter_conditions) == 0:
            return None
        elif len(filter_conditions) == 1:
            return filter_conditions[0]
        else:
            return {"$and": filter_conditions}
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        sql_filters: Optional[Dict[str, Any]] = None,
        vector_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining vector similarity with SQL filtering.
        
        Args:
            query: User query
            top_k: Number of results
            sql_filters: SQL-based filters (for future implementation)
            vector_weight: Weight for vector search (0-1)
            
        Returns:
            List of retrieved chunks
        """
        # For now, use vector search with metadata filters
        # Future: combine with SQL queries for exact matches
        return self.retrieve(query, top_k=top_k, filters=sql_filters)

