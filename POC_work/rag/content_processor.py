"""
Content Processor for MTG Articles
Processes scraped articles into chunks suitable for vector embedding.
"""

import json
import re
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ContentChunker:
    """Chunks articles into smaller pieces for embedding."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize chunker.
        
        Args:
            chunk_size: Target size of chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Split on sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_text(self, text: str, metadata: Dict) -> List[Dict]:
        """
        Chunk text into smaller pieces.
        
        Args:
            text: Text to chunk
            metadata: Metadata to attach to each chunk
            
        Returns:
            List of chunk dictionaries
        """
        if not text or len(text) < self.chunk_size:
            # Text is short enough, return as single chunk
            return [{
                'text': text,
                'chunk_index': 0,
                'metadata': metadata
            }]
        
        # Split into sentences
        sentences = self.split_text(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence would exceed chunk size, save current chunk
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'metadata': {**metadata, 'chunk_index': chunk_index}
                })
                chunk_index += 1
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0:
                    # Keep last few sentences for overlap
                    overlap_text = ' '.join(current_chunk[-3:])  # Last 3 sentences
                    current_chunk = [overlap_text] if len(overlap_text) < self.chunk_size else []
                    current_length = len(overlap_text) if current_chunk else 0
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space
        
        # Add remaining chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'chunk_index': chunk_index,
                'metadata': {**metadata, 'chunk_index': chunk_index}
            })
        
        return chunks


class ContentProcessor:
    """Processes scraped articles for vector database."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """Initialize processor."""
        self.chunker = ContentChunker(chunk_size, chunk_overlap)
    
    def clean_article(self, article: Dict) -> Optional[Dict]:
        """Clean and validate an article."""
        if not article.get('content'):
            return None
        
        content = article['content'].strip()
        if len(content) < 200:  # Skip very short articles
            return None
        
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r' {2,}', ' ', content)
        
        return {
            'url': article.get('url', ''),
            'title': article.get('title', 'Untitled'),
            'content': content,
            'source': article.get('source', 'unknown'),
            'author': article.get('author', ''),
            'date': article.get('date', ''),
            'scraped_at': article.get('scraped_at', ''),
            'word_count': len(content.split())
        }
    
    def process_article(self, article: Dict) -> List[Dict]:
        """
        Process a single article into chunks.
        
        Returns:
            List of chunk dictionaries ready for embedding
        """
        cleaned = self.clean_article(article)
        if not cleaned:
            return []
        
        # Create metadata for chunks
        metadata = {
            'url': cleaned['url'],
            'title': cleaned['title'],
            'source': cleaned['source'],
            'author': cleaned.get('author', ''),
            'date': cleaned.get('date', ''),
            'content_type': 'article',
            'word_count': cleaned['word_count']
        }
        
        # Chunk the content
        chunks = self.chunker.chunk_text(cleaned['content'], metadata)
        
        # Add unique IDs to chunks
        for i, chunk in enumerate(chunks):
            chunk['chunk_id'] = f"{cleaned['source']}_{hash(cleaned['url'])}_{i}"
            chunk['metadata']['chunk_id'] = chunk['chunk_id']
        
        return chunks
    
    def process_articles_file(self, file_path: str) -> List[Dict]:
        """Process all articles from a JSON file."""
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return []
        
        logger.info(f"Loading articles from {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        logger.info(f"Processing {len(articles)} articles...")
        all_chunks = []
        
        for i, article in enumerate(articles, 1):
            chunks = self.process_article(article)
            all_chunks.extend(chunks)
            if i % 10 == 0:
                logger.info(f"Processed {i}/{len(articles)} articles, {len(all_chunks)} chunks so far")
        
        logger.info(f"Created {len(all_chunks)} chunks from {len(articles)} articles")
        return all_chunks
    
    def save_chunks(self, chunks: List[Dict], output_file: str):
        """Save processed chunks to JSON file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(chunks)} chunks to {output_path}")


def main():
    """Main function to process articles."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python content_processor.py <articles_json_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "processed_chunks.json"
    
    processor = ContentProcessor(chunk_size=1000, chunk_overlap=200)
    chunks = processor.process_articles_file(input_file)
    processor.save_chunks(chunks, output_file)
    
    print(f"\nProcessing complete!")
    print(f"Created {len(chunks)} chunks from articles")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()

