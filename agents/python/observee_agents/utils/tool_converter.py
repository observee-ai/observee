"""
Tool conversion utilities for converting between different tool formats
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import hashlib

logger = logging.getLogger(__name__)


class ToolConverter:
    """Handles conversion of tools between different formats with caching"""
    
    def __init__(self):
        self._tool_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_key: Optional[str] = None
    
    def _compute_tools_hash(self, tools: List[Any]) -> str:
        """Compute a lightweight hash of the tools list to detect changes"""
        # Fast signature-based approach
        tool_signatures = []
        
        for tool in tools:
            if hasattr(tool, '__dict__'):
                # FastMCP tool object
                name = getattr(tool, 'name', '')
                desc_len = len(getattr(tool, 'description', ''))
                schema = getattr(tool, 'inputSchema', {})
            else:
                # Already a dict
                name = tool.get('name', '')
                desc_len = len(tool.get('description', ''))
                schema = tool.get('inputSchema', {})
            
            # Create lightweight signature: name + desc length + schema keys
            schema_keys = ''
            if isinstance(schema, dict) and 'properties' in schema:
                schema_keys = ','.join(sorted(schema['properties'].keys()))
            
            tool_signatures.append(f"{name}:{desc_len}:{schema_keys}")
        
        # Create final hash from count + sorted signatures
        signature = f"{len(tools)}|{'|'.join(sorted(tool_signatures))}"
        return hashlib.md5(signature.encode()).hexdigest()
    
    def _should_update_cache(self, tools: List[Any]) -> bool:
        """Check if cache needs to be updated based on tools list"""
        new_hash = self._compute_tools_hash(tools)
        
        if self._cache_key != new_hash:
            logger.debug(f"Tool cache needs update. Old hash: {self._cache_key}, New hash: {new_hash}")
            return True
        
        return False
    
    
    def convert_to_anthropic_format(self, tools: List[Any], use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Convert tools to Anthropic/MCP internal format with caching
        
        Args:
            tools: List of tools (FastMCP tool objects or dicts)
            use_cache: Whether to use caching
            
        Returns:
            List of tools in Anthropic format
        """
        # Check if we should use cache
        if use_cache and not self._should_update_cache(tools):
            logger.debug(f"Using cached Anthropic tools ({len(self._tool_cache.get('anthropic', []))} tools)")
            return self._tool_cache.get('anthropic', [])
        
        # Convert tools
        anthropic_tools = []
        for tool in tools:
            anthropic_tool = self._convert_single_tool_to_anthropic(tool)
            if anthropic_tool:
                anthropic_tools.append(anthropic_tool)
        
        # Update cache
        if use_cache:
            self._cache_key = self._compute_tools_hash(tools)
            self._tool_cache['anthropic'] = anthropic_tools
            logger.debug(f"Updated Anthropic tool cache with {len(anthropic_tools)} tools")
        
        return anthropic_tools
    
    def _convert_single_tool_to_anthropic(self, tool: Any) -> Optional[Dict[str, Any]]:
        """Convert a single tool to Anthropic format"""
        try:
            # Extract tool properties
            if hasattr(tool, '__dict__'):
                # FastMCP tool object
                name = getattr(tool, 'name', '')
                description = getattr(tool, 'description', '')
                input_schema = getattr(tool, 'inputSchema', {})
            else:
                # Already a dict
                name = tool.get('name', '')
                description = tool.get('description', '')
                input_schema = tool.get('inputSchema', {})
            
            if not name:
                logger.warning("Tool has no name, skipping")
                return None
            
            # Build Anthropic format
            anthropic_tool = {
                "name": name,
                "description": description or "",
                "inputSchema": input_schema or {"type": "object", "properties": {}}
            }
            
            return anthropic_tool
            
        except Exception as e:
            logger.error(f"Error converting tool to Anthropic format: {e}")
            return None
    
    def convert_custom_tools(self, custom_tools: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Convert custom tools from OpenAI format and extract their names
        
        Args:
            custom_tools: List of custom tools in OpenAI format
            
        Returns:
            Tuple of (converted_tools, tool_names)
        """
        converted_tools = []
        tool_names = []
        
        if not custom_tools:
            return converted_tools, tool_names
        
        for custom_tool in custom_tools:
            # Convert OpenAI format to internal format
            if custom_tool.get("type") == "function" and "function" in custom_tool:
                func = custom_tool["function"]
                converted_tool = {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "inputSchema": func.get("parameters", {"type": "object", "properties": {}})
                }
                converted_tools.append(converted_tool)
                
                if func.get("name"):
                    tool_names.append(func["name"])
        
        return converted_tools, tool_names
    
    def clear_cache(self):
        """Clear the tool cache"""
        self._tool_cache.clear()
        self._cache_key = None
        logger.debug("Tool cache cleared")


# Global tool converter instance
_tool_converter = ToolConverter()


def convert_tools_to_anthropic(tools: List[Any], use_cache: bool = True) -> List[Dict[str, Any]]:
    """
    Convert tools to Anthropic/MCP internal format
    
    Args:
        tools: List of tools (FastMCP tool objects or dicts)
        use_cache: Whether to use caching (default: True)
        
    Returns:
        List of tools in Anthropic format
    """
    return _tool_converter.convert_to_anthropic_format(tools, use_cache)


def convert_custom_tools(custom_tools: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Convert custom tools from OpenAI format and extract their names
    
    Args:
        custom_tools: List of custom tools in OpenAI format
        
    Returns:
        Tuple of (converted_tools, tool_names)
    """
    return _tool_converter.convert_custom_tools(custom_tools)


def clear_tool_cache():
    """Clear the global tool cache"""
    _tool_converter.clear_cache()