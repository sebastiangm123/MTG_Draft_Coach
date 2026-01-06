"""
Vector Database Pipeline
Processes article chunks and stores them in a vector database for RAG.
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
import logging

# Workaround for sqlite3 version issue on Windows
try:
    import pysqlite3
    import sys
    sys.modules['sqlite3'] = pysqlite3
except ImportError:
    pass  # Use system sqlite3 if pysqlite3 not available

import chromadb
from chromadb.config import Settings
import openai
from tqdm import tqdm

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for text chunks."""
    
    def __init__(self, model: str = "openai", api_key: Optional[str] = None):
        """
        Initialize embedding generator.
        
        Args:
            model: "openai" for OpenAI embeddings, "local" for sentence-transformers
            api_key: OpenAI API key (if using OpenAI)
        """
        self.model_type = model
        
        if model == "openai":
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
            self.client = openai.OpenAI(api_key=api_key)
            self.model_name = "text-embedding-3-small"  # Cost-effective option
        elif model == "local":
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Loaded local embedding model: all-MiniLM-L6-v2")
            except ImportError:
                raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")
        else:
            raise ValueError(f"Unknown model: {model}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if self.model_type == "openai":
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return response.data[0].embedding
        else:
            return self.model.encode(text, convert_to_numpy=False).tolist()
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches."""
        all_embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch = texts[i:i + batch_size]
            
            if self.model_type == "openai":
                try:
                    response = self.client.embeddings.create(
                        model=self.model_name,
                        input=batch
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                except Exception as e:
                    logger.error(f"Error generating embeddings: {e}")
                    # Fallback to individual requests
                    batch_embeddings = [self.generate_embedding(text) for text in batch]
            else:
                # sentence-transformers encode returns list when convert_to_numpy=False
                batch_embeddings = self.model.encode(batch, convert_to_numpy=False)
                # Ensure it's a list of lists
                if not isinstance(batch_embeddings[0], list):
                    batch_embeddings = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in batch_embeddings]
            
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings


class VectorDBPipeline:
    """Pipeline to process chunks and store in vector database."""
    
    def __init__(self, db_path: str = "./vector_db", embedding_model: str = "openai", api_key: Optional[str] = None):
        """
        Initialize pipeline.
        
        Args:
            db_path: Path to ChromaDB database
            embedding_model: "openai" or "local"
            api_key: OpenAI API key (if using OpenAI)
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="mtg_articles",
            metadata={"description": "MTG article content for RAG"}
        )
        
        # Initialize embedding generator
        self.embedder = EmbeddingGenerator(model=embedding_model, api_key=api_key)
        
        logger.info(f"Initialized vector database at {self.db_path}")
        logger.info(f"Collection contains {self.collection.count()} documents")
    
    def process_chunks(self, chunks: List[Dict], batch_size: int = 100) -> int:
        """
        Process chunks and store in vector database.
        
        Args:
            chunks: List of chunk dictionaries
            batch_size: Batch size for embedding generation
            
        Returns:
            Number of chunks processed
        """
        if not chunks:
            logger.warning("No chunks to process")
            return 0
        
        logger.info(f"Processing {len(chunks)} chunks...")
        
        # Extract texts and metadata
        texts = [chunk['text'] for chunk in chunks]
        ids = [chunk['chunk_id'] for chunk in chunks]
        metadatas = []
        
        for chunk in chunks:
            metadata = chunk.get('metadata', {}).copy()
            # ChromaDB requires metadata values to be strings, numbers, or booleans
            # Convert any complex types
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_metadata[key] = value
                else:
                    clean_metadata[key] = str(value)
            metadatas.append(clean_metadata)
        
        # Generate embeddings in batches
        logger.info("Generating embeddings...")
        embeddings = self.embedder.generate_embeddings_batch(texts, batch_size=batch_size)
        
        # Store in ChromaDB in batches
        logger.info("Storing in vector database...")
        db_batch_size = 100
        
        for i in tqdm(range(0, len(chunks), db_batch_size), desc="Storing chunks"):
            batch_ids = ids[i:i + db_batch_size]
            batch_texts = texts[i:i + db_batch_size]
            batch_embeddings = embeddings[i:i + db_batch_size]
            batch_metadatas = metadatas[i:i + db_batch_size]
            
            try:
                self.collection.add(
                    ids=batch_ids,
                    embeddings=batch_embeddings,
                    documents=batch_texts,
                    metadatas=batch_metadatas
                )
            except Exception as e:
                logger.error(f"Error storing batch {i}: {e}")
                # Try adding individually
                for j, (chunk_id, text, embedding, metadata) in enumerate(
                    zip(batch_ids, batch_texts, batch_embeddings, batch_metadatas)
                ):
                    try:
                        self.collection.add(
                            ids=[chunk_id],
                            embeddings=[embedding],
                            documents=[text],
                            metadatas=[metadata]
                        )
                    except Exception as e2:
                        logger.error(f"Error storing chunk {chunk_id}: {e2}")
        
        logger.info(f"Successfully stored {self.collection.count()} documents in vector database")
        return len(chunks)
    
    def process_chunks_file(self, chunks_file: str, batch_size: int = 100) -> int:
        """Process chunks from a JSON file."""
        chunks_path = Path(chunks_file)
        if not chunks_path.exists():
            logger.error(f"File not found: {chunks_path}")
            return 0
        
        logger.info(f"Loading chunks from {chunks_path}")
        with open(chunks_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        
        return self.process_chunks(chunks, batch_size=batch_size)
    
    def search(self, query: str, n_results: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search the vector database.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = self.embedder.generate_embedding(query)
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filters
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return formatted_results
    
    def get_stats(self) -> Dict:
        """Get statistics about the vector database."""
        count = self.collection.count()
        
        # Get sample to analyze sources
        sample = self.collection.get(limit=min(100, count))
        sources = {}
        if sample['metadatas']:
            for metadata in sample['metadatas']:
                source = metadata.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
        
        return {
            'total_chunks': count,
            'sources': sources
        }


def main():
    """Main function to run the pipeline."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python vector_db_pipeline.py <chunks_json_file> [--model openai|local] [--db-path <path>]")
        sys.exit(1)
    
    chunks_file = sys.argv[1]
    model = "openai"
    db_path = "./vector_db"
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--db-path" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    # Initialize pipeline
    pipeline = VectorDBPipeline(db_path=db_path, embedding_model=model)
    
    # Process chunks
    print(f"Processing chunks from {chunks_file}...")
    print(f"Using embedding model: {model}")
    print(f"Vector database path: {db_path}")
    
    processed = pipeline.process_chunks_file(chunks_file)
    
    # Print stats
    stats = pipeline.get_stats()
    print(f"\nPipeline complete!")
    print(f"Processed {processed} chunks")
    print(f"Total documents in database: {stats['total_chunks']}")
    print(f"Sources: {stats['sources']}")
    
    # Test search
    print("\nTesting search...")
    results = pipeline.search("What are the best draft strategies?", n_results=3)
    print(f"Found {len(results)} results")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['metadata'].get('title', 'No title')}")
        print(f"   Source: {result['metadata'].get('source', 'unknown')}")
        print(f"   Text preview: {result['text'][:200]}...")


if __name__ == "__main__":
    main()

