"""
Base agent interface and shared types
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    @abstractmethod
    async def initialize(self):
        """Initialize the agent and its resources"""
        pass
    
    @abstractmethod
    async def chat(
        self, 
        message: str, 
        max_tools: int = 20, 
        min_score: float = 8.0,
        context: Optional[Dict[str, Any]] = None,
        execute_tools: bool = True,
        custom_tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Chat with the agent
        
        Args:
            message: User message
            max_tools: Maximum number of tools to include
            min_score: Minimum relevance score for tools
            context: Optional context for tool filtering
            execute_tools: Whether to execute tool calls
            custom_tools: Optional list of custom tools
            
        Returns:
            Response dictionary with content and metadata
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        message: str,
        max_tools: int = 20,
        min_score: float = 8.0,
        custom_tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat responses"""
        pass
    
    @abstractmethod
    def reset_conversation(self):
        """Reset the conversation history"""
        pass
    
    @abstractmethod
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history"""
        pass


class AgentResponse:
    """Structured response from agent"""
    
    def __init__(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        filtered_tools_count: int = 0,
        filtered_tools: Optional[List[str]] = None,
        used_filtering: bool = False
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.filtered_tools_count = filtered_tools_count
        self.filtered_tools = filtered_tools or []
        self.used_filtering = used_filtering
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "filtered_tools_count": self.filtered_tools_count,
            "filtered_tools": self.filtered_tools,
            "used_filtering": self.used_filtering
        }