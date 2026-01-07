#!/usr/bin/env python3
"""
Context Assembler for MTG Draft Coach RAG System

Part 7 of RAG Components Plan:
- Combine retrieved chunks into LLM prompt
- Chunk selection and token management
- Formatting for optimal LLM understanding
- Metadata inclusion for citations
"""

from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ContextAssembler:
    """
    Assembles retrieved chunks into formatted context for LLM prompts.
    """
    
    def __init__(
        self,
        max_tokens: int = 4000,
        max_chunks: int = 10,
        include_metadata: bool = True
    ):
        """
        Initialize context assembler.
        
        Args:
            max_tokens: Maximum tokens for context (default: 4000 for GPT-4)
            max_chunks: Maximum number of chunks to include
            include_metadata: Whether to include metadata in context
        """
        self.max_tokens = max_tokens
        self.max_chunks = max_chunks
        self.include_metadata = include_metadata
    
    def assemble(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        user_query: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assemble retrieved chunks into formatted context.
        
        Args:
            retrieved_chunks: List of retrieved chunks from vector database
            user_query: Original user query
            system_prompt: Optional system prompt
            
        Returns:
            Dictionary with 'prompt', 'context', 'chunks_used', 'tokens_estimated'
        """
        # Select most relevant chunks
        selected_chunks = self._select_chunks(retrieved_chunks)
        
        # Format context
        context_text = self._format_context(selected_chunks)
        
        # Build full prompt
        prompt = self._build_prompt(
            context_text=context_text,
            user_query=user_query,
            system_prompt=system_prompt
        )
        
        # Estimate tokens (rough: 1 token ≈ 4 characters)
        tokens_estimated = len(prompt) // 4
        
        return {
            'prompt': prompt,
            'context': context_text,
            'chunks_used': len(selected_chunks),
            'tokens_estimated': tokens_estimated,
            'chunk_details': [
                {
                    'id': chunk.get('id'),
                    'type': chunk.get('metadata', {}).get('chunk_type'),
                    'distance': chunk.get('distance'),
                    'source': self._get_source_info(chunk)
                }
                for chunk in selected_chunks
            ]
        }
    
    def _select_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select most relevant chunks, respecting token limits.
        
        Args:
            chunks: List of retrieved chunks (already sorted by relevance)
            
        Returns:
            Selected chunks
        """
        selected = []
        current_tokens = 0
        
        for chunk in chunks[:self.max_chunks]:
            chunk_text = chunk.get('document', '')
            chunk_tokens = len(chunk_text) // 4  # Rough estimate
            
            if current_tokens + chunk_tokens <= self.max_tokens:
                selected.append(chunk)
                current_tokens += chunk_tokens
            else:
                # Try to fit partial chunk if there's room
                remaining_tokens = self.max_tokens - current_tokens
                if remaining_tokens > 100:  # At least 100 tokens worth
                    # Truncate chunk text
                    truncated_text = chunk_text[:remaining_tokens * 4]
                    chunk_copy = chunk.copy()
                    chunk_copy['document'] = truncated_text + "..."
                    selected.append(chunk_copy)
                break
        
        return selected
    
    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Format chunks into readable context text.
        
        Args:
            chunks: Selected chunks
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found."
        
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            chunk_text = chunk.get('document', '')
            metadata = chunk.get('metadata', {})
            
            # Add chunk header with metadata if enabled
            if self.include_metadata:
                source_info = self._get_source_info(chunk)
                if source_info:
                    context_parts.append(f"[Chunk {i} - {source_info}]")
            
            context_parts.append(chunk_text)
            
            # Add separator between chunks
            if i < len(chunks):
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    def _get_source_info(self, chunk: Dict[str, Any]) -> str:
        """
        Get source information from chunk metadata.
        
        Args:
            chunk: Chunk dictionary
            
        Returns:
            Source information string
        """
        metadata = chunk.get('metadata', {})
        chunk_type = metadata.get('chunk_type', 'unknown')
        
        if chunk_type == 'card':
            card_name = metadata.get('card_name', 'Unknown Card')
            set_code = metadata.get('set', '')
            return f"Card: {card_name.title()}" + (f" ({set_code})" if set_code else "")
        elif chunk_type == 'archetype':
            colors = metadata.get('main_colors', '')
            set_code = metadata.get('set', '')
            return f"Archetype: {colors}" + (f" ({set_code})" if set_code else "")
        elif chunk_type == 'draft_pattern':
            set_code = metadata.get('set', '')
            return f"Draft Pattern" + (f" ({set_code})" if set_code else "")
        else:
            return "Unknown Source"
    
    def _build_prompt(
        self,
        context_text: str,
        user_query: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Build full prompt with system prompt, context, and user query.
        
        Args:
            context_text: Formatted context
            user_query: User's question
            system_prompt: Optional custom system prompt
            
        Returns:
            Complete prompt string
        """
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        prompt_parts = [
            system_prompt,
            "",
            "CONTEXT:",
            context_text,
            "",
            f"USER QUESTION: {user_query}",
            "",
            "Answer based on the context above. If the context doesn't contain enough information, say so. Be specific and cite the data when possible."
        ]
        
        return "\n".join(prompt_parts)
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for MTG Draft Coach."""
        return """You are an expert MTG Draft Coach with access to comprehensive draft statistics and card performance data.

Your role is to help players make better drafting decisions by:
- Analyzing card performance statistics (win rates, pick numbers, etc.)
- Explaining archetype strengths and strategies
- Providing pick-by-pick advice
- Comparing cards and archetypes
- Giving draft direction recommendations

Use the provided context data to answer questions accurately. When citing statistics, be specific about the numbers and sample sizes. If the context doesn't contain enough information to fully answer a question, acknowledge this limitation."""
    
    def format_for_chat(
        self,
        retrieved_chunks: List[Dict[str, Any]],
        user_query: str
    ) -> List[Dict[str, str]]:
        """
        Format context for OpenAI chat API format.
        
        Args:
            retrieved_chunks: Retrieved chunks
            user_query: User query
            
        Returns:
            List of message dictionaries for chat API
        """
        assembled = self.assemble(retrieved_chunks, user_query)
        
        messages = [
            {
                "role": "system",
                "content": self._get_default_system_prompt()
            },
            {
                "role": "user",
                "content": assembled['prompt']
            }
        ]
        
        return messages

