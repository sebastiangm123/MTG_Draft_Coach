#!/usr/bin/env python3
"""
LLM Integration for MTG Draft Coach RAG System

Part 8 of RAG Components Plan:
- Enhanced OpenAI integration with context
- System prompt for draft coaching
- Response formatting
- Citation and source tracking
"""

import os
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging

# Import existing OpenAI chat
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from openai_chat import OpenAIChat

from rag.context_assembler import ContextAssembler

logger = logging.getLogger(__name__)


class MTGDraftCoachLLM:
    """
    Enhanced LLM integration for MTG Draft Coach with RAG context.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        max_tokens: int = 2000,
        temperature: float = 0.7
    ):
        """
        Initialize LLM integration.
        
        Args:
            api_key: OpenAI API key (if None, reads from env)
            model: Model to use (default: gpt-4)
            max_tokens: Maximum tokens for response
            temperature: Temperature for response generation
        """
        self.chat = OpenAIChat(api_key=api_key, model=model)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.context_assembler = ContextAssembler(max_tokens=4000)
        
        # Set system prompt
        self.chat.set_system_prompt(self._get_system_prompt())
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for MTG Draft Coach."""
        return """You are an expert MTG Draft Coach with access to comprehensive draft statistics and card performance data.

Your role is to help players make better drafting decisions by:
- Analyzing card performance statistics (win rates, pick numbers, etc.)
- Explaining archetype strengths and strategies
- Providing pick-by-pick advice
- Comparing cards and archetypes
- Giving draft direction recommendations

Use the provided context data to answer questions accurately. When citing statistics, be specific about the numbers and sample sizes. If the context doesn't contain enough information to fully answer a question, acknowledge this limitation.

Be conversational but informative. Format your responses clearly with proper structure."""
    
    def answer_with_context(
        self,
        user_query: str,
        retrieved_chunks: List[Dict[str, Any]],
        reset_conversation: bool = False
    ) -> Dict[str, Any]:
        """
        Generate answer using retrieved context.
        
        Args:
            user_query: User's question
            retrieved_chunks: Retrieved chunks from vector database
            reset_conversation: Whether to start new conversation
            
        Returns:
            Dictionary with 'answer', 'sources', 'tokens_used', etc.
        """
        # Assemble context
        assembled = self.context_assembler.assemble(
            retrieved_chunks=retrieved_chunks,
            user_query=user_query
        )
        
        # Format for chat API
        messages = self.context_assembler.format_for_chat(
            retrieved_chunks=retrieved_chunks,
            user_query=user_query
        )
        
        # Get response from LLM
        try:
            response = self.chat.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            answer = response.choices[0].message.content
            
            # Extract source information
            sources = [
                {
                    'id': chunk.get('id'),
                    'type': chunk.get('metadata', {}).get('chunk_type'),
                    'source': self.context_assembler._get_source_info(chunk),
                    'distance': chunk.get('distance')
                }
                for chunk in assembled['chunk_details']
            ]
            
            return {
                'answer': answer,
                'sources': sources,
                'chunks_used': assembled['chunks_used'],
                'tokens_estimated': assembled['tokens_estimated'],
                'context_length': len(assembled['context'])
            }
        
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise
    
    def answer_simple(self, query: str) -> str:
        """
        Simple answer without context (for testing).
        
        Args:
            query: User query
            
        Returns:
            Answer string
        """
        return self.chat.chat(query, reset_conversation=False)
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.chat.clear_history()
        self.chat.set_system_prompt(self._get_system_prompt())

