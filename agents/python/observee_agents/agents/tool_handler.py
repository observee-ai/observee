"""
Tool handling, filtering, and execution logic
"""

from typing import List, Dict, Any, Optional, Tuple
from fastmcp import Client
import logging
import json

from ..search import create_filter
from ..search.cloud_infrastructure import VectorStoreManager
from ..utils.tool_converter import convert_tools_to_anthropic, convert_custom_tools

logger = logging.getLogger(__name__)


class ToolHandler:
    """Handles tool filtering, conversion, and execution"""
    
    def __init__(
        self,
        mcp_client: Client,
        enable_filtering: bool = True,
        filter_type: Optional[str] = None,
        sync_tools: bool = True,
        server_name: str = "observee",
        server_url: str = None
    ):
        """
        Initialize tool handler
        
        Args:
            mcp_client: FastMCP client instance
            enable_filtering: Whether to enable tool filtering
            filter_type: Type of filter to use (bm25, cloud, etc.)
            sync_tools: Whether to sync tools with cloud
            server_name: Name of the MCP server
            server_url: URL of the MCP server
        """
        self.mcp = mcp_client
        self.enable_filtering = enable_filtering
        self.all_tools = []
        
        # Initialize tool filter only if filtering is enabled
        if enable_filtering:
            # Determine filter type - default is always bm25
            if filter_type is None:
                filter_type = "bm25"
            
            # Initialize vector store manager for cloud filters
            self.vector_store_manager = None
            if filter_type == "cloud":
                try:
                    self.vector_store_manager = VectorStoreManager(
                        use_cloud=True,
                        sync_tools=sync_tools
                    )
                    logger.debug("Vector store manager initialized for cloud search")
                except Exception as e:
                    logger.warning(f"Failed to initialize vector store: {e}. Falling back to BM25.")
                    filter_type = "bm25"
            
            # Create tool filter
            self.tool_filter = create_filter(
                filter_type=filter_type,
                vector_store_manager=self.vector_store_manager,
                sync_tools=sync_tools
            )
            self.tool_filter.set_server_info(server_name, server_url)
            
            logger.info(f"Using {filter_type} filter for tool search")
        else:
            self.tool_filter = None
            self.vector_store_manager = None
            logger.info("Tool filtering disabled")
    
    async def load_tools(self) -> List[Any]:
        """Load all available tools from MCP"""
        tools = await self.mcp.list_tools()
        self.all_tools = tools
        
        # Add tools to filter if filtering is enabled
        if self.enable_filtering and self.tool_filter:
            self.tool_filter.add_tools(tools)
        
        logger.debug(f"Loaded {len(tools)} tools")
        if self.enable_filtering and self.tool_filter:
            logger.debug(f"Categories discovered: {self.tool_filter.get_categories()}")
        
        return tools
    
    async def filter_tools(
        self,
        query: str,
        max_tools: int = 20,
        min_score: float = 8.0,
        context: Optional[Dict[str, Any]] = None,
        expand_by_server: bool = False
    ) -> Tuple[List[Any], List[str]]:
        """
        Filter tools based on query
        
        Args:
            query: The search query
            max_tools: Maximum number of tools to return
            min_score: Minimum score threshold
            context: Optional context for filtering
            expand_by_server: If True, include all tools from the same server when a tool is selected
        
        Returns:
            Tuple of (filtered_tools, tool_names)
        """
        if not self.enable_filtering or not self.tool_filter:
            # Return all tools when filtering is disabled
            return self.all_tools, [t.name for t in self.all_tools]
        
        filtered_tools = await self.tool_filter.filter_tools(
            query, 
            max_tools=max_tools, 
            min_score=min_score, 
            context=context
        )
        
        # If expand_by_server is enabled, include all tools from the same servers
        if expand_by_server and filtered_tools:
            
            # Extract unique server names from filtered tools
            servers_found = set()
            original_tool_names = []
            for tool in filtered_tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                original_tool_names.append(tool_name)
                if '__' in tool_name:
                    server = tool_name.split('__')[0]
                    servers_found.add(server)
            
            
            # If we found any servers, expand to include all tools from those servers
            if servers_found:
                expanded_tools = []
                expanded_tool_names = set()
                server_tool_count = {server: 0 for server in servers_found}
                
                # First add all originally filtered tools
                for tool in filtered_tools:
                    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                    if tool_name not in expanded_tool_names:
                        expanded_tools.append(tool)
                        expanded_tool_names.add(tool_name)
                
                # Then add all other tools from the same servers
                added_tools = []
                for tool in self.all_tools:
                    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                    if tool_name not in expanded_tool_names:
                        if '__' in tool_name:
                            tool_server = tool_name.split('__')[0]
                            if tool_server in servers_found:
                                expanded_tools.append(tool)
                                expanded_tool_names.add(tool_name)
                                added_tools.append(tool_name)
                                server_tool_count[tool_server] += 1
                
                for server, count in server_tool_count.items():
                    logger.debug(f"   • {server}: +{count} tools")
                
                logger.debug(f"Expanded from {len(filtered_tools)} to {len(expanded_tools)} tools by including all tools from servers: {servers_found}")
                filtered_tools = expanded_tools
            
        
        logger.debug(f"Filtered to {len(filtered_tools)} relevant tools for query: '{query}'")
        if filtered_tools:
            logger.debug(f"Top tools: {[t.name for t in filtered_tools[:5]]}")
        
        return filtered_tools, [t.name for t in filtered_tools]
    
    
    def get_original_tools(self, filtered_tools: List[Any]) -> List[Any]:
        """Get original tool objects with full schemas for filtered tools"""
        original_tools = []
        for filtered_tool in filtered_tools:
            original_tool = next((t for t in self.all_tools if t.name == filtered_tool.name), None)
            if original_tool:
                original_tools.append(original_tool)
        return original_tools
    
    def prepare_tools_for_provider(
        self,
        tools: List[Any],
        custom_tools: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Prepare tools for LLM provider
        
        Returns:
            Tuple of (converted_tools, all_tool_names)
        """
        # Convert to Anthropic format
        converted_tools = convert_tools_to_anthropic(tools)
        tool_names = [t.name for t in tools]
        
        # Add custom tools if provided
        if custom_tools:
            custom_converted, custom_names = convert_custom_tools(custom_tools)
            converted_tools.extend(custom_converted)
            tool_names.extend(custom_names)
        
        return converted_tools, tool_names
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool call through MCP"""
        try:
            result = await self.mcp.call_tool(tool_name, tool_input)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise
    
    def parse_tool_calls(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse tool calls from LLM response"""
        tool_calls = []
        
        for tc in response.get("tool_calls", []):
            if tc.get("type") == "function":
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                
                tool_calls.append({
                    "name": func.get("name"),
                    "input": args
                })
        
        return tool_calls