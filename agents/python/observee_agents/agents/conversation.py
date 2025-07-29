"""
Conversation and message history management
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history and message formatting"""
    
    def __init__(self, system_prompt: Optional[str] = None):
        """
        Initialize conversation manager
        
        Args:
            system_prompt: Default system prompt to use
        """
        self.messages: List[Dict[str, str]] = []
        self.system_prompt = system_prompt or self._default_system_prompt()
    
    def _default_system_prompt(self) -> str:
        """Get default system prompt"""
        return (
            "You are a helpful AI assistant with access to various tools. "
            "Always use the appropriate tools to answer questions when they are available."
        )
    
    def add_message(self, role: str, content: str):
        """Add a message to the conversation history"""
        self.messages.append({"role": role, "content": content})
        logger.debug(f"Added {role} message to conversation history")
    
    def get_messages_with_system(self) -> List[Dict[str, str]]:
        """Get all messages with system prompt prepended"""
        return [{"role": "system", "content": self.system_prompt}] + self.messages
    
    def get_messages_for_langchain(self):
        """Convert messages to LangChain format"""
        from langchain.schema import HumanMessage, SystemMessage, AIMessage
        
        langchain_messages = []
        
        for msg in self.messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
            elif msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
        
        return langchain_messages
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the most recent user message"""
        for msg in reversed(self.messages):
            if msg["role"] == "user":
                return msg["content"]
        return None
    
    def reset(self):
        """Clear conversation history"""
        self.messages = []
        logger.debug("Conversation history cleared")
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get a copy of the conversation history"""
        return self.messages.copy()
    
    def set_system_prompt(self, prompt: str):
        """Update the system prompt"""
        self.system_prompt = prompt
        logger.debug("System prompt updated")