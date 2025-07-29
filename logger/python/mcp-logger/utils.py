"""Utility functions for the Observee SDK."""

import json
from typing import Any, Dict, Optional


# MCP internal fields that should be filtered from logs
MCP_INTERNAL_FIELDS = {"server_session_id", "mcp_customer_id", "mcp_client_id"}

# Keywords used to detect prompt-type functions
PROMPT_KEYWORDS = ['prompt', 'template', 'message']


def safe_json_serialize(data: Dict[str, Any]) -> str:
    """
    Safely serialize a dictionary to JSON, filtering out non-serializable objects.
    
    This function ensures that all values in the dictionary can be serialized
    to JSON. Non-serializable values are replaced with a string representation.
    
    Args:
        data: Dictionary to serialize
        
    Returns:
        JSON string with only serializable values
        
    Example:
        >>> data = {"name": "test", "func": lambda x: x}
        >>> result = safe_json_serialize(data)
        >>> # result will be: '{"name": "test", "func": "<non-serializable: function>"}'
    """
    def is_json_serializable(obj: Any) -> bool:
        """Check if an object is JSON serializable."""
        try:
            json.dumps(obj)
            return True
        except (TypeError, ValueError):
            return False
    
    # Filter out non-serializable values
    safe_data = {}
    for key, value in data.items():
        if is_json_serializable(value):
            safe_data[key] = value
        else:
            # Replace with a string representation for logging purposes
            safe_data[key] = f"<non-serializable: {type(value).__name__}>"
    
    return json.dumps(safe_data)


def extract_session_id(kwargs: Dict[str, Any], arguments_dict: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Extract session ID from various possible locations.
    
    This function checks multiple locations where a session ID might be stored,
    supporting both direct kwargs and MCP-style arguments.
    
    Args:
        kwargs: Keyword arguments from the function call
        arguments_dict: MCP-style arguments dictionary
        
    Returns:
        Session ID if found, None otherwise
        
    Example:
        >>> # Direct kwargs
        >>> session_id = extract_session_id({"session_id": "abc123"}, None)
        >>> assert session_id == "abc123"
        >>> 
        >>> # MCP-style arguments
        >>> session_id = extract_session_id({}, {"server_session_id": "xyz789"})
        >>> assert session_id == "xyz789"
    """
    # Check direct kwargs first
    if "session_id" in kwargs:
        return kwargs["session_id"]
    elif "server_session_id" in kwargs:
        return kwargs["server_session_id"]
    elif arguments_dict and isinstance(arguments_dict, dict):
        # Check for MCP-style session ID in arguments dict
        return arguments_dict.get("server_session_id")
    return None


def filter_mcp_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter out MCP internal fields from a dictionary.
    
    Removes fields that are internal to MCP and shouldn't be logged
    such as customer IDs and internal session identifiers.
    
    Args:
        data: Dictionary to filter
        
    Returns:
        Dictionary with MCP internal fields removed
        
    Example:
        >>> data = {"name": "test", "mcp_customer_id": "123", "value": 42}
        >>> filtered = filter_mcp_fields(data)
        >>> assert filtered == {"name": "test", "value": 42}
    """
    return {k: v for k, v in data.items() if k not in MCP_INTERNAL_FIELDS}


def format_response(response: Any) -> str:
    """
    Format response data for logging.
    
    Handles various response types including lists of objects with text attributes.
    This is particularly useful for MCP responses which often contain structured
    objects with text content.
    
    Args:
        response: Response data to format
        
    Returns:
        String representation of the response
        
    Example:
        >>> # Simple string
        >>> assert format_response("Hello") == "Hello"
        >>> 
        >>> # List of objects with text attribute
        >>> class TextObj:
        ...     def __init__(self, text):
        ...         self.text = text
        >>> response = [TextObj("Line 1"), TextObj("Line 2")]
        >>> assert format_response(response) == "Line 1\\nLine 2"
    """
    if isinstance(response, list):
        # Handle list of TextContent objects or similar
        parts = []
        for item in response:
            if hasattr(item, 'content') and hasattr(item.content, 'text'):
                parts.append(item.content.text)
            elif hasattr(item, 'text'):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return "\n".join(parts)
    else:
        return str(response)