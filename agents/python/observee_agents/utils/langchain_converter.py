"""
LangChain converter for MCP tools - converts filtered MCP tools to LangChain format
"""

import re
from typing import Any, NoReturn, Dict, Optional, List
from jsonschema_pydantic import jsonschema_to_pydantic
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, create_model
from fastmcp import Client
import logging

logger = logging.getLogger(__name__)


class LangChainConverter:
    """Converter for converting MCP tools to LangChain tools."""
    
    def __init__(self, mcp_client: Client, disallowed_tools: Optional[List[str]] = None):
        """
        Initialize the LangChain converter.
        
        Args:
            mcp_client: The FastMCP client instance
            disallowed_tools: List of tool names that should not be converted
        """
        self.mcp_client = mcp_client
        self.disallowed_tools = disallowed_tools or []
    
    def fix_schema(self, schema: dict) -> dict:
        """
        Convert JSON Schema 'type': ['string', 'null'] to 'anyOf' format.
        
        Args:
            schema: The JSON schema to fix.
            
        Returns:
            The fixed JSON schema.
        """
        if isinstance(schema, dict):
            if "type" in schema and isinstance(schema["type"], list):
                schema["anyOf"] = [{"type": t} for t in schema["type"]]
                del schema["type"]  # Remove 'type' and standardize to 'anyOf'
            for key, value in schema.items():
                schema[key] = self.fix_schema(value)  # Apply recursively
        return schema
    
    def convert_tool_to_langchain(self, mcp_tool: Any) -> Optional[BaseTool]:
        """
        Convert a single MCP tool to LangChain's tool format.
        
        Args:
            mcp_tool: The MCP tool object (from FastMCP)
            
        Returns:
            A LangChain BaseTool or None if tool is disallowed
        """
        # Skip disallowed tools
        if mcp_tool.name in self.disallowed_tools:
            return None
        
        logger.debug(f"Converting tool: {mcp_tool.name}")
        logger.debug(f"Tool description: {mcp_tool.description}")
        logger.debug(f"Tool type: {type(mcp_tool)}")
        logger.debug(f"Tool attributes: {dir(mcp_tool)}")
        logger.debug(f"Tool schema: {getattr(mcp_tool, 'inputSchema', 'No schema')}")
        
        # Create a reference to self for use in the dynamic class
        converter_self = self
        mcp_client = self.mcp_client
        
        class McpToLangChainConverter(BaseTool):
            # Keep the original tool name - don't sanitize
            name: str = mcp_tool.name or "NO_NAME"
            description: str = mcp_tool.description or ""
            
            # Convert JSON schema to Pydantic model for argument validation
            args_schema: type[BaseModel] = jsonschema_to_pydantic(
                converter_self.fix_schema(mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {"type": "object", "properties": {}})
            )
            handle_tool_error: bool = True
            
            def __repr__(self) -> str:
                return f"MCP tool: {self.name}: {self.description}"
            
            def _run(self, **kwargs: Any) -> NoReturn:
                """Synchronous run method that always raises an error."""
                raise NotImplementedError("MCP tools only support async operations")
            
            async def _arun(self, **kwargs: Any) -> Any:
                """
                Asynchronously execute the tool with given arguments.
                
                Args:
                    kwargs: The arguments to pass to the tool.
                    
                Returns:
                    The result of the tool execution.
                    
                Raises:
                    ToolException: If tool execution fails.
                """
                logger.debug(f'MCP tool: "{self.name}" received input: {kwargs}')
                
                try:
                    # Call the tool through the MCP client
                    # If kwargs is empty but the tool expects a 'q' parameter, try to extract from somewhere
                    if not kwargs and "search" in self.name.lower():
                        # This is a hack for search tools that expect a 'q' parameter
                        # but LangChain might be passing it differently
                        logger.warning(f"Empty kwargs for search tool {self.name}, this might be a schema issue")
                    
                    result = await mcp_client.call_tool(self.name, kwargs)
                    
                    # Parse the result
                    if isinstance(result, dict):
                        # If result has 'content' field, extract it
                        if 'content' in result:
                            content = result['content']
                            if isinstance(content, list):
                                # Handle list of content items
                                decoded_result = ""
                                for item in content:
                                    if isinstance(item, dict):
                                        if item.get('type') == 'text':
                                            decoded_result += item.get('text', '')
                                        elif item.get('type') == 'image':
                                            decoded_result += f"[Image: {item.get('data', 'No data')}]"
                                        else:
                                            decoded_result += str(item)
                                    else:
                                        decoded_result += str(item)
                                return decoded_result
                            else:
                                return str(content)
                        else:
                            return str(result)
                    else:
                        return str(result)
                    
                except Exception as e:
                    if self.handle_tool_error:
                        return f"Error executing MCP tool: {str(e)}"
                    raise
        
        return McpToLangChainConverter()
    
    def convert_tools_to_langchain(self, mcp_tools: List[Any]) -> List[BaseTool]:
        """
        Convert a list of MCP tools to LangChain tools.
        
        Args:
            mcp_tools: List of MCP tool objects
            
        Returns:
            List of LangChain BaseTool objects
        """
        langchain_tools = []
        
        for tool in mcp_tools:
            converted_tool = self.convert_tool_to_langchain(tool)
            if converted_tool:
                langchain_tools.append(converted_tool)
        
        logger.info(f"Converted {len(langchain_tools)} MCP tools to LangChain format")
        return langchain_tools 