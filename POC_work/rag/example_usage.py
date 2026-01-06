"""
Example usage of the vector database for RAG queries.
Demonstrates how to search the knowledge base.
"""

from vector_db_pipeline import VectorDBPipeline
import os

def main():
    """Example usage of the vector database."""
    
    # Initialize pipeline
    # Use the same embedding model you used to build the database
    model = os.getenv("EMBEDDING_MODEL", "openai")  # or "local"
    db_path = "./vector_db"
    
    print(f"Loading vector database from {db_path}...")
    print(f"Using embedding model: {model}")
    
    try:
        pipeline = VectorDBPipeline(db_path=db_path, embedding_model=model)
        
        # Get stats
        stats = pipeline.get_stats()
        print(f"\nDatabase Stats:")
        print(f"  Total chunks: {stats['total_chunks']}")
        print(f"  Sources: {stats['sources']}")
        
        # Example queries
        queries = [
            "What are the best draft strategies?",
            "How do I evaluate cards in limited format?",
            "What makes a good mana curve?",
            "How should I prioritize removal spells?",
            "What are the key signals in pack 1?",
        ]
        
        print("\n" + "=" * 60)
        print("Example Searches")
        print("=" * 60)
        
        for query in queries:
            print(f"\nQuery: {query}")
            print("-" * 60)
            
            results = pipeline.search(query, n_results=3)
            
            if results:
                for i, result in enumerate(results, 1):
                    title = result['metadata'].get('title', 'No title')
                    source = result['metadata'].get('source', 'unknown')
                    distance = result.get('distance', 'N/A')
                    
                    print(f"\n{i}. {title}")
                    print(f"   Source: {source}")
                    print(f"   Similarity: {distance:.4f}" if isinstance(distance, float) else f"   Similarity: {distance}")
                    print(f"   Preview: {result['text'][:150]}...")
            else:
                print("  No results found")
        
        # Search with filters
        print("\n" + "=" * 60)
        print("Filtered Search Example")
        print("=" * 60)
        
        # Search only in ChannelFireball articles
        print("\nQuery: 'draft strategy' (filtered to ChannelFireball)")
        results = pipeline.search(
            "draft strategy",
            n_results=3,
            filters={"source": "channelfireball"}
        )
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. {result['metadata'].get('title', 'No title')}")
        else:
            print("No results found")
        
    except FileNotFoundError:
        print(f"\nError: Vector database not found at {db_path}")
        print("Please run build_knowledge_base.py first to create the database.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

