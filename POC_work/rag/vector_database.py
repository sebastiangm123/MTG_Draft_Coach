#!/usr/bin/env python3
"""
Vector Database for MTG Draft Coach RAG System

Part 5 of RAG Components Plan:
- Store embeddings in ChromaDB
- Enable similarity search
- Metadata filtering
- Production-ready with persistence
"""

import os
import json
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class VectorDatabase:
    """
    Vector database interface using ChromaDB.
    Stores embeddings with metadata for similarity search.
    """
    
    def __init__(
        self,
        db_path: str = "./vector_db",
        collection_name: str = "mtg_draft_coach",
        reset: bool = False
    ):
        """
        Initialize vector database.
        
        Args:
            db_path: Path to store ChromaDB database
            collection_name: Name of the collection
            reset: If True, delete existing collection and start fresh
        """
        # Workaround for sqlite3 version issue - must be done BEFORE importing chromadb
        try:
            import pysqlite3
            import sys
            sys.modules['sqlite3'] = pysqlite3
        except ImportError:
            pass  # Use system sqlite3 if pysqlite3 not available
        
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "chromadb required. Install with: pip install chromadb"
            )
        
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        if reset:
            try:
                self.client.delete_collection(collection_name)
                logger.info(f"Deleted existing collection: {collection_name}")
            except Exception:
                pass
        
        try:
            self.collection = self.client.get_collection(collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "MTG Draft Coach RAG embeddings"}
            )
            logger.info(f"Created new collection: {collection_name}")
    
    def add_chunks(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        batch_size: int = 100
    ):
        """
        Add chunks to the vector database.
        
        Args:
            chunk_ids: List of unique chunk IDs
            embeddings: List of embedding vectors
            texts: List of chunk texts
            metadatas: List of metadata dictionaries
            batch_size: Number of chunks to add per batch
        """
        if not all(len(lst) == len(chunk_ids) for lst in [embeddings, texts, metadatas]):
            raise ValueError("All lists must have the same length")
        
        total = len(chunk_ids)
        logger.info(f"Adding {total} chunks to vector database...")
        
        # Process in batches
        for i in range(0, total, batch_size):
            batch_ids = chunk_ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]
            batch_texts = texts[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            # Clean metadata: remove None values (ChromaDB doesn't accept None)
            cleaned_metadatas = []
            for metadata in batch_metadatas:
                cleaned = {k: v for k, v in metadata.items() if v is not None}
                cleaned_metadatas.append(cleaned)
            
            try:
                self.collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_texts,
                    metadatas=cleaned_metadatas
                )
                logger.debug(f"Added batch {i//batch_size + 1}: {len(batch_ids)} chunks")
            except Exception as e:
                logger.error(f"Error adding batch {i//batch_size + 1}: {e}")
                raise
        
        logger.info(f"Successfully added {total} chunks to vector database")
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Metadata filters (deprecated, use where)
            where: Metadata where clause for filtering
            
        Returns:
            List of result dictionaries with id, distance, document, metadata
        """
        # Use where if provided, otherwise use filters for backward compatibility
        where_clause = where or filters
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'distance': results['distances'][0][i] if results.get('distances') else None,
                        'document': results['documents'][0][i] if results.get('documents') else None,
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else None
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            raise
    
    def get_by_ids(self, chunk_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieve chunks by their IDs.
        
        Args:
            chunk_ids: List of chunk IDs to retrieve (duplicates will be removed)
            
        Returns:
            List of chunk dictionaries
        """
        try:
            # Remove duplicates while preserving order
            unique_ids = list(dict.fromkeys(chunk_ids))
            
            if not unique_ids:
                return []
            
            results = self.collection.get(ids=unique_ids)
            
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        'id': results['ids'][i],
                        'document': results['documents'][i] if results.get('documents') else None,
                        'metadata': results['metadatas'][i] if results.get('metadatas') else None
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error retrieving chunks by IDs: {e}")
            raise
    
    def delete_chunks(self, chunk_ids: List[str]):
        """Delete chunks by their IDs."""
        try:
            self.collection.delete(ids=chunk_ids)
            logger.info(f"Deleted {len(chunk_ids)} chunks from vector database")
        except Exception as e:
            logger.error(f"Error deleting chunks: {e}")
            raise
    
    def count(self) -> int:
        """Get total number of chunks in the database."""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error counting chunks: {e}")
            return 0
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "total_chunks": count,
                "db_path": str(self.db_path)
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {
                "collection_name": self.collection_name,
                "total_chunks": 0,
                "db_path": str(self.db_path),
                "error": str(e)
            }
    
    def reset_collection(self):
        """Reset the collection (delete all chunks)."""
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "MTG Draft Coach RAG embeddings"}
            )
            logger.info(f"Reset collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            raise

