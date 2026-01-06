"""
OpenAI Chat Interface
Simple programmatic interface for chatting with OpenAI via Python.
"""

import os
from openai import OpenAI
from typing import List, Dict, Optional


class OpenAIChat:
    """Simple interface for chatting with OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """
        Initialize OpenAI chat client.
        
        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
    
    def chat(self, message: str, system_prompt: Optional[str] = None, 
             reset_conversation: bool = False) -> str:
        """
        Send a message to OpenAI and get a response.
        
        Args:
            message: User message
            system_prompt: Optional system prompt (only used if reset_conversation is True)
            reset_conversation: If True, start a new conversation
        
        Returns:
            Assistant's response
        """
        if reset_conversation:
            self.conversation_history = []
            if system_prompt:
                self.conversation_history.append({
                    "role": "system",
                    "content": system_prompt
                })
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.conversation_history
            )
            
            # Extract assistant response
            assistant_message = response.choices[0].message.content
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return assistant_message
            
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            raise
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history.copy()
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
    
    def set_system_prompt(self, prompt: str):
        """Set or update the system prompt."""
        # Remove existing system prompt if any
        self.conversation_history = [
            msg for msg in self.conversation_history 
            if msg.get("role") != "system"
        ]
        # Add new system prompt at the beginning
        self.conversation_history.insert(0, {
            "role": "system",
            "content": prompt
        })


def main():
    """Example usage of the OpenAI chat interface."""
    # Initialize chat (will use OPENAI_API_KEY from environment)
    try:
        chat = OpenAIChat(model="gpt-4")
        
        # Example: Simple chat
        print("Starting chat with OpenAI...")
        response = chat.chat("Hello! Can you help me with Magic the Gathering drafting?")
        print(f"Assistant: {response}")
        
        # Continue conversation
        response = chat.chat("What makes a good first pick in a draft?")
        print(f"Assistant: {response}")
        
        # Example with system prompt
        chat.clear_history()
        chat.set_system_prompt(
            "You are an expert Magic the Gathering draft coach. "
            "Provide concise, actionable advice for drafting."
        )
        response = chat.chat("Should I pick Lightning Bolt or Counterspell first?")
        print(f"\nAssistant (with system prompt): {response}")
        
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your OPENAI_API_KEY environment variable.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()

