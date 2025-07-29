"""
Cloud-based tool filtering using Pinecone vector search (with optional hybrid BM25)
"""

from typing import List, Dict, Any, Optional
import logging
import asyncio

from .base import BaseToolFilter, Tool
from .cloud_infrastructure import VectorStoreManager

logger = logging.getLogger(__name__)


class CloudFilter(BaseToolFilter):
    """
    Cloud-based tool filtering using VectorStoreManager.
    The manager already handles hybrid search (semantic + BM25) in Pinecone.
    Requires Pinecone and OpenAI API keys.
    """
    
    def __init__(self, sync_tools: bool = True, hybrid: bool = True, **kwargs):
        """
        Initialize cloud filter
        
        Args:
            sync_tools: Whether to sync tools to cloud storage
        """
        # Extract vector store manager if provided
        vector_store_manager = kwargs.pop('vector_store_manager', None)
        
        super().__init__(vector_store_manager=vector_store_manager)
        
        # Initialize categories tracking
        self.categories = {}  # Dict[str, List[Tool]]
        
        # If no vector store manager provided, create one
        if not self.vector_store_manager:
            self.vector_store_manager = VectorStoreManager(
                use_cloud=True,
                sync_tools=sync_tools
            )
        
        self.hybrid = hybrid  # Whether to use hybrid search (BM25 + semantic)
        self._sync_task = None
    
    def add_tools(self, tools: List[Any]) -> None:
        """Add tools and sync to cloud"""
        # Store tools locally for reference
        for tool_data in tools:
            if hasattr(tool_data, 'name'):  # Tool object
                tool = Tool(
                    name=tool_data.name,
                    description=tool_data.description or "",
                    server=self._extract_server_from_name(tool_data.name),
                    parameters=tool_data.inputSchema if hasattr(tool_data, 'inputSchema') else {}
                )
            else:  # Dict format
                tool = Tool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    server=tool_data.get("server", self._extract_server_from_name(tool_data.get("name", ""))),
                    parameters=tool_data.get("inputSchema", {})
                )
            
            self.tools.append(tool)
            
            # Track categories
            category = tool.server.lower()
            if category not in self.categories:
                self.categories[category] = []
            self.categories[category].append(tool)
        
        # Sync to cloud if server info available
        if self.vector_store_manager and self.server_name and self.server_url:
            # Convert to dict format for vector store
            tool_dicts = []
            for tool_data in tools:
                if hasattr(tool_data, 'name'):  # Tool object
                    tool_dict = {
                        "name": tool_data.name,
                        "description": tool_data.description or "",
                        "inputSchema": tool_data.inputSchema if hasattr(tool_data, 'inputSchema') else {},
                        "category": self._extract_server_from_name(tool_data.name)
                    }
                else:  # Already dict
                    tool_dict = tool_data
                tool_dicts.append(tool_dict)
            
            # Sync tools asynchronously
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Store the sync task
                    self._sync_task = asyncio.create_task(
                        self.vector_store_manager.sync_tools_to_cloud(
                            tool_dicts, self.server_name, self.server_url
                        )
                    )
                else:
                    # Run synchronously if no event loop
                    loop.run_until_complete(
                        self.vector_store_manager.sync_tools_to_cloud(
                            tool_dicts, self.server_name, self.server_url
                        )
                    )
            except Exception as e:
                logger.warning(f"Failed to sync tools to cloud: {e}")
        
        logger.debug(f"Added {len(self.tools)} tools to cloud filter")
    
    async def filter_tools(
        self, 
        query: str, 
        max_tools: int = 20, 
        min_score: float = 5.0, 
        context: Dict[str, Any] = None
    ) -> List[Tool]:
        """Filter tools using cloud vector search"""
        if not self.vector_store_manager:
            logger.warning("No vector store manager available")
            return []
        
        try:
            # Wait for sync to complete if in progress
            if self._sync_task and not self._sync_task.done():
                await self._sync_task
            
            # Get currently available tool names
            available_tool_names = [tool.name for tool in self.tools]
            
            # Search in vector store
            vector_results = await self.vector_store_manager.search_tools(
                query=query,
                top_k=max_tools * 2,  # Get more candidates for filtering
                available_tool_names=available_tool_names
            )
            
            # Convert results to Tool objects
            if not vector_results:
                logger.warning("No results from vector search")
                return []
            
            # Create tool lookup
            tool_dict = {tool.name: tool for tool in self.tools}
            
            # Filter and convert results
            filtered_tools = []
            for tool_data, score in vector_results[:max_tools]:
                tool_name = tool_data.get("name")
                if tool_name in tool_dict:
                    # Apply context boosts if needed
                    if context and 'tool_hints' in context:
                        for hint in context['tool_hints']:
                            hint_lower = hint.lower()
                            if hint_lower in tool_name.lower():
                                score += 0.1  # Small boost for hints
                    
                    filtered_tools.append(tool_dict[tool_name])
            
            logger.debug(f"Cloud filter returned {len(filtered_tools)} tools for query: '{query}'")
            if filtered_tools:
                logger.debug(f"Top 3 tools: {[t.name for t in filtered_tools[:3]]}")
            
            return filtered_tools
            
        except Exception as e:
            logger.error(f"Cloud search failed: {e}")
            # Don't fall back to local search - fail explicitly
            raise
    
    def get_categories(self) -> List[str]:
        """Get all discovered categories"""
        return sorted(list(self.categories.keys()))
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """Get all tools in a specific category"""
        return list(self.categories.get(category.lower(), []))