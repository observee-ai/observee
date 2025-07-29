"""Data models for the Observee SDK."""

from typing import Optional

from pydantic import BaseModel


class ToolUsageData(BaseModel):
    """
    Data model for tool usage logging.
    
    This model captures all relevant information about a tool execution
    including timing, inputs, outputs, and metadata.
    
    Attributes:
        mcp_server_name: Name of the MCP server
        tool_name: Name of the tool being executed
        tool_input: JSON-serialized input data (only included with API key)
        tool_response: Tool execution response (only included with API key)
        duration: Execution duration in milliseconds
        session_id: Optional session identifier for tracking related executions
        
    Example:
        >>> data = ToolUsageData(
        ...     mcp_server_name="my-server",
        ...     tool_name="calculator",
        ...     tool_input='{"operation": "add", "a": 5, "b": 3}',
        ...     tool_response="8",
        ...     duration=15.2,
        ...     session_id="abc123"
        ... )
    """
    mcp_server_name: str
    tool_name: str
    tool_input: Optional[str] = None
    tool_response: Optional[str] = None
    duration: float
    session_id: Optional[str] = None


class PromptUsageData(BaseModel):
    """
    Data model for prompt usage logging.
    
    This model captures all relevant information about a prompt execution
    including inputs, outputs, and metadata.
    
    Attributes:
        mcp_server_name: Name of the MCP server
        prompt_name: Name of the prompt being executed
        prompt_input: JSON-serialized input data (only included with API key)
        prompt_response: Prompt execution response (only included with API key)
        session_id: Optional session identifier for tracking related executions
        
    Example:
        >>> data = PromptUsageData(
        ...     mcp_server_name="my-server",
        ...     prompt_name="greeting",
        ...     prompt_input='{"name": "Alice"}',
        ...     prompt_response="Hello, Alice!",
        ...     session_id="xyz789"
        ... )
    """
    mcp_server_name: str
    prompt_name: str
    prompt_input: Optional[str] = None
    prompt_response: Optional[str] = None
    session_id: Optional[str] = None