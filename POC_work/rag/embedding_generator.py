#!/usr/bin/env python3
"""
Embedding Generator for MTG Draft Coach RAG System

Part 4 of RAG Components Plan:
- Generate embeddings for text chunks
- Support OpenAI and local embeddings
- Batch processing for efficiency
- Error handling and retry logic
"""

import os
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates embeddings for text chunks.
    Supports OpenAI and local embedding models.
    """
    
    def __init__(
        self,
        model: str = "openai",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """
        Initialize embedding generator.
        
        Args:
            model: "openai" for OpenAI embeddings, "local" for sentence-transformers
            api_key: OpenAI API key (if using OpenAI, otherwise reads from env)
            model_name: Specific model name (optional)
        """
        self.model_type = model.lower()
        
        if self.model_type == "openai":
            self._init_openai(api_key, model_name)
        elif self.model_type == "local":
            self._init_local(model_name)
        else:
            raise ValueError(f"Unknown model type: {model}. Use 'openai' or 'local'")
    
    def _init_openai(self, api_key: Optional[str], model_name: Optional[str]):
        """Initialize OpenAI embedding client."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = model_name or "text-embedding-3-small"  # Cost-effective, good quality
        self.dimension = None  # Will be determined on first call
        
        logger.info(f"Initialized OpenAI embedding generator with model: {self.model_name}")
    
    def _init_local(self, model_name: Optional[str]):
        """Initialize local embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers required. Install with: pip install sentence-transformers"
            )
        
        model_name = model_name or "all-MiniLM-L6-v2"  # Fast, good quality
        logger.info(f"Loading local embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"Loaded local embedding model: {model_name} (dimension: {self.dimension})")
    
    def generate_embedding(self, text: str, retries: int = 3) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            retries: Number of retry attempts on failure
            
        Returns:
            Embedding vector as list of floats
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if self.model_type == "openai":
            return self._generate_openai_embedding(text, retries)
        else:
            return self._generate_local_embedding(text)
    
    def _generate_openai_embedding(self, text: str, retries: int) -> List[float]:
        """Generate embedding using OpenAI API."""
        for attempt in range(retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=text
                )
                embedding = response.data[0].embedding
                
                # Cache dimension
                if self.dimension is None:
                    self.dimension = len(embedding)
                
                return embedding
            except Exception as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"OpenAI API error (attempt {attempt + 1}/{retries}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to generate OpenAI embedding after {retries} attempts: {e}")
                    raise
    
    def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        try:
            embedding = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate local embedding: {e}")
            raise
    
    def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per batch
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = []
        
        if show_progress:
            try:
                from tqdm import tqdm
                iterator = tqdm(range(0, len(texts), batch_size), desc="Generating embeddings")
            except ImportError:
                iterator = range(0, len(texts), batch_size)
        else:
            iterator = range(0, len(texts), batch_size)
        
        for i in iterator:
            batch = texts[i:i + batch_size]
            
            if self.model_type == "openai":
                batch_embeddings = self._generate_openai_batch(batch)
            else:
                batch_embeddings = self._generate_local_batch(batch)
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def _generate_openai_batch(self, texts: List[str], retries: int = 3) -> List[List[float]]:
        """Generate embeddings for a batch using OpenAI API."""
        for attempt in range(retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=texts
                )
                embeddings = [item.embedding for item in response.data]
                return embeddings
            except Exception as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"OpenAI API batch error (attempt {attempt + 1}/{retries}): {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to generate OpenAI batch embeddings after {retries} attempts: {e}")
                    raise
    
    def _generate_local_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch using local model."""
        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                batch_size=len(texts)
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate local batch embeddings: {e}")
            raise
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if self.dimension is None:
            # Generate a test embedding to determine dimension
            test_embedding = self.generate_embedding("test")
            self.dimension = len(test_embedding)
        return self.dimension
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model."""
        return {
            "model_type": self.model_type,
            "model_name": self.model_name,
            "dimension": self.get_dimension()
        }

