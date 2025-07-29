"""
Base filter class for tool filtering strategies
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class Tool:
    """Represents a tool with its metadata"""
    name: str
    description: str
    server: str
    parameters: Dict[str, Any] = None
    categories: Set[str] = field(default_factory=set)
    keywords: Set[str] = field(default_factory=set)
    
    def __hash__(self):
        """Make Tool hashable by using name as unique identifier"""
        return hash(self.name)


class BaseToolFilter(ABC):
    """Abstract base class for tool filtering strategies"""
    
    def __init__(self, vector_store_manager=None):
        """
        Initialize the filter
        
        Args:
            vector_store_manager: Optional vector store manager for cloud-based filters
        """
        self.tools: List[Tool] = []
        self.server_name: Optional[str] = None
        self.server_url: Optional[str] = None
        self.vector_store_manager = vector_store_manager
    
    def set_server_info(self, server_name: str, server_url: str):
        """Set server information for vector store operations"""
        self.server_name = server_name
        self.server_url = server_url
    
    @abstractmethod
    def add_tools(self, tools: List[Any]) -> None:
        """Add tools to the filter"""
        pass
    
    @abstractmethod
    async def filter_tools(
        self, 
        query: str, 
        max_tools: int = 20, 
        min_score: float = 5.0, 
        context: Dict[str, Any] = None
    ) -> List[Tool]:
        """
        Filter tools based on query
        
        Args:
            query: The user query
            max_tools: Maximum number of tools to return
            min_score: Minimum score threshold
            context: Optional context for filtering
            
        Returns:
            List of relevant tools
        """
        pass
    
    def get_categories(self) -> List[str]:
        """Get all discovered categories"""
        return []
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category"""
        return []
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools"""
        return self.tools.copy()
    
    def _extract_server_from_name(self, tool_name: str) -> str:
        """Extract server name from tool name"""
        if '__' in tool_name:
            return tool_name.split('__')[0]
        return "default"