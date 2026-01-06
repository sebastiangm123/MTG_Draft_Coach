"""Quick script to check vector database contents."""
import chromadb
import json

client = chromadb.PersistentClient(path='knowledge_base_output/vector_db')
collection = client.get_collection('mtg_articles')

print(f"Total documents in vector database: {collection.count()}")

if collection.count() > 0:
    # Get a sample
    sample = collection.get(limit=5)
    print(f"\nSample of {len(sample['ids'])} documents:")
    print("=" * 60)
    
    for i, (doc_id, metadata, document) in enumerate(zip(sample['ids'], sample['metadatas'], sample['documents']), 1):
        print(f"\n{i}. Document ID: {doc_id}")
        print(f"   Title: {metadata.get('title', 'N/A')}")
        print(f"   Source: {metadata.get('source', 'N/A')}")
        print(f"   Content Type: {metadata.get('content_type', 'N/A')}")
        print(f"   Word Count: {metadata.get('word_count', 'N/A')}")
        print(f"   Text Preview: {document[:200]}...")
        print()
    
    # Get statistics
    all_metadata = collection.get()['metadatas']
    sources = {}
    for meta in all_metadata:
        source = meta.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    print("\n" + "=" * 60)
    print("Statistics by Source:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count} documents")
else:
    print("\nVector database is empty - processing phase failed (needs OpenAI API key)")

