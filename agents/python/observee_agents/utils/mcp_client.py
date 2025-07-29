"""
Lightweight MCP client for direct server operations without LLM overhead
"""

from typing import List, Dict, Any, Optional
from fastmcp import Client
import logging

logger = logging.getLogger(__name__)


class MCPDirectClient:
    """Direct MCP client for operations that don't need LLM integration"""
    
    def __init__(self, server_url: str, auth_token: Optional[str] = None, server_name: str = "observee"):
        """
        Initialize MCP direct client
        
        Args:
            server_url: MCP server URL
            auth_token: Optional authentication token
            server_name: Server name for configuration
        """
        self.server_url = server_url
        self.auth_token = auth_token
        self.server_name = server_name
        self._client = None
        self._tools_cache = None
        
    async def __aenter__(self):
        """Enter async context"""
        # Create MCP configuration
        config = {
            "mcpServers": {
                self.server_name: {
                    "url": self.server_url
                }
            }
        }
        
        # Add auth header if token provided
        if self.auth_token:
            config["mcpServers"][self.server_name]["headers"] = {
                "Authorization": f"Bearer {self.auth_token}"
            }
        
        # Create and initialize client
        self._client = Client(config)
        await self._client.__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context"""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools from the MCP server
        
        Returns:
            List of tools with name, description, and input schema
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Use cached tools if available
        if self._tools_cache is not None:
            return self._tools_cache
        
        # Get tools from MCP server
        tools = await self._client.list_tools()
        
        # Convert to our format - handle Tool objects from fastmcp
        self._tools_cache = [
            {
                "name": tool.name if hasattr(tool, 'name') else tool["name"],
                "description": tool.description if hasattr(tool, 'description') else tool.get("description", ""),
                "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else tool.get("inputSchema", {})
            }
            for tool in tools
        ]
        
        return self._tools_cache
    
    async def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific tool
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool information or None if not found
        """
        tools = await self.list_tools()
        
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        
        return None
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Execute a tool with given parameters
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            
        Returns:
            Tool execution result
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        # Execute the tool
        result = await self._client.call_tool(tool_name, tool_input)
        return result


# Singleton instance management for performance
_client_cache = {}

async def get_mcp_client(
    server_url: str, 
    auth_token: Optional[str] = None, 
    server_name: str = "observee",
    force_new: bool = False
) -> MCPDirectClient:
    """
    Get or create an MCP client (with caching for performance)
    
    Args:
        server_url: MCP server URL
        auth_token: Optional authentication token
        server_name: Server name
        force_new: Force creation of new client
        
    Returns:
        MCPDirectClient instance
    """
    cache_key = f"{server_url}:{server_name}:{auth_token or 'noauth'}"
    
    if not force_new and cache_key in _client_cache:
        return _client_cache[cache_key]
    
    client = MCPDirectClient(server_url, auth_token, server_name)
    _client_cache[cache_key] = client
    
    return client