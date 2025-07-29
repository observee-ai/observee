"""
Observee Agents - A Python SDK for MCP tool integration with LLM providers
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

from .agents.agent import MCPAgent
from .auth import call_mcpauth_login, get_available_servers, get_servers_by_client, McpAuthClient, McpAuthError
from .utils.mcp_client import MCPDirectClient

# Load environment variables
load_dotenv()

__all__ = [
    "chat_with_tools", "chat_with_tools_stream", "MCPAgent", "list_tools", "get_tool_info", "filter_tools", "execute_tool",
    "call_mcpauth_login", "get_available_servers", "get_servers_by_client", "McpAuthClient", "McpAuthError",
    "clear_session", "clear_all_sessions", "list_sessions", "get_conversation_history", "reset_conversation_history"
]

# Global agent registry for conversation sessions
_agent_sessions = {}

class ConversationSession:
    """Manages conversation state for enhanced chat functions"""
    def __init__(self, session_id: str, agent: MCPAgent):
        self.session_id = session_id
        self.agent = agent
        self.created_at = asyncio.get_event_loop().time()
        self.last_used = self.created_at
    
    def update_last_used(self):
        self.last_used = asyncio.get_event_loop().time()

async def _get_or_create_session(
    session_id: Optional[str],
    provider: str,
    model: Optional[str],
    observee_url: Optional[str],
    observee_api_key: Optional[str],
    client_id: Optional[str],
    server_name: str,
    filter_type: str,
    enable_filtering: bool,
    sync_tools: bool,
    system_prompt: Optional[str],
    **provider_kwargs
) -> ConversationSession:
    """Get or create a conversation session"""
    global _agent_sessions
    
    # Generate session ID if not provided
    if session_id is None:
        import uuid
        session_id = str(uuid.uuid4())
    
    # Check if session exists
    if session_id in _agent_sessions:
        session = _agent_sessions[session_id]
        session.update_last_used()
        return session
    
    # Create new session
    config = _get_observee_config(observee_url, observee_api_key, client_id)
    
    agent = MCPAgent(
        provider=provider,
        model=model,
        server_name=server_name,
        server_url=config["url"],
        auth_token=config["auth_token"],
        sync_tools=sync_tools,
        filter_type=filter_type,
        enable_filtering=enable_filtering,
        system_prompt=system_prompt,
        **provider_kwargs
    )
    
    # Initialize agent
    await agent.__aenter__()
    
    # Create session
    session = ConversationSession(session_id, agent)
    _agent_sessions[session_id] = session
    
    return session

def clear_session(session_id: str):
    """Clear a specific conversation session"""
    global _agent_sessions
    if session_id in _agent_sessions:
        session = _agent_sessions[session_id]
        # Close the agent properly
        asyncio.create_task(session.agent.__aexit__(None, None, None))
        del _agent_sessions[session_id]

def clear_all_sessions():
    """Clear all conversation sessions"""
    global _agent_sessions
    for session_id in list(_agent_sessions.keys()):
        clear_session(session_id)

def list_sessions() -> List[str]:
    """List all active session IDs"""
    global _agent_sessions
    return list(_agent_sessions.keys())

def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """Get conversation history for a session"""
    global _agent_sessions
    if session_id not in _agent_sessions:
        raise ValueError(f"Session {session_id} not found")
    
    return _agent_sessions[session_id].agent.get_conversation_history()

def reset_conversation_history(session_id: str):
    """Reset conversation history for a session"""
    global _agent_sessions
    if session_id not in _agent_sessions:
        raise ValueError(f"Session {session_id} not found")
    
    _agent_sessions[session_id].agent.reset_conversation()


def _get_observee_config(
    observee_url: Optional[str] = None, 
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None
):
    """
    Get Observee configuration with priority: params > env vars
    
    Args:
        observee_url: Direct URL (if provided, client_id will be replaced/added)
        observee_api_key: API key for authentication
        client_id: Client ID (from params or env var)
    
    Returns:
        dict: Configuration with 'url' and optional 'auth_token'
    
    Raises:
        ValueError: If no configuration is provided
    """
    # Get client_id with priority: param > env var
    if not client_id:
        client_id = os.getenv("OBSERVEE_CLIENT_ID")
    
    def _update_client_id_in_url(url: str, new_client_id: str) -> str:
        """Replace or add client_id in URL"""
        import re
        
        # If client_id already exists, replace it
        if "client_id=" in url:
            # Replace existing client_id value
            url = re.sub(r'client_id=[^&]*', f'client_id={new_client_id}', url)
        else:
            # Add client_id to URL if we have a client_id
            if new_client_id:
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}client_id={new_client_id}"
        
        return url
    
    # Priority 1: Direct URL parameter
    if observee_url:
        if client_id:
            updated_url = _update_client_id_in_url(observee_url, client_id)
        else:
            updated_url = observee_url
        return {
            "url": updated_url,
            "auth_token": None
        }
    
    # Priority 2: API key parameter
    if observee_api_key:
        if not client_id:
            raise ValueError("client_id is required when using observee_api_key. Set OBSERVEE_CLIENT_ID env var or pass client_id parameter.")
        
        url = f"https://mcp.observee.ai/mcp?client_id={client_id}"
        return {
            "url": url,
            "auth_token": observee_api_key
        }
    
    # Priority 3: Environment variables
    env_url = os.getenv("OBSERVEE_URL")
    if env_url:
        if client_id:
            updated_url = _update_client_id_in_url(env_url, client_id)
        else:
            updated_url = env_url
        return {
            "url": updated_url,
            "auth_token": None
        }
    
    env_api_key = os.getenv("OBSERVEE_API_KEY")
    if env_api_key:
        if not client_id:
            raise ValueError("client_id is required when using OBSERVEE_API_KEY. Set OBSERVEE_CLIENT_ID env var or pass client_id parameter.")
        
        url = f"https://mcp.observee.ai/mcp?client_id={client_id}"
        return {
            "url": url,
            "auth_token": env_api_key
        }
    
    # No configuration provided
    raise ValueError(
        "No Observee configuration found. Please provide one of:\n"
        "1. observee_url parameter or OBSERVEE_URL env var\n"
        "2. observee_api_key parameter or OBSERVEE_API_KEY env var (requires client_id)\n"
        "3. Set environment variables in .env file"
    )

async def _chat_with_tools_async(
    message: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee",
    max_tools: int = 20,
    min_score: float = 8.0,
    filter_type: str = "bm25",
    enable_filtering: bool = True,
    sync_tools: bool = False,
    custom_tools: Optional[List[Dict[str, Any]]] = None,
    custom_tool_handler: Optional[callable] = None,
    **provider_kwargs
) -> Dict[str, Any]:
    """
    Internal async function to handle the actual chat with tools logic
    """
    # Get configuration
    config = _get_observee_config(observee_url, observee_api_key, client_id)
    
    # Create and use agent with async context manager (like main.py/simpletest.py)
    async with MCPAgent(
        provider=provider,
        model=model,
        server_name=server_name,
        server_url=config["url"],
        auth_token=config["auth_token"],
        sync_tools=sync_tools,
        filter_type=filter_type,
        enable_filtering=enable_filtering,
        **provider_kwargs
    ) as agent:
        # Execute the chat with tools
        result = await agent.chat_with_tools(
            message=message,
            max_tools=max_tools,
            min_score=min_score,
            custom_tools=custom_tools,
            custom_tool_handler=custom_tool_handler
        )
        
        return result

def chat_with_tools(
    message: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee",
    max_tools: int = 20,
    min_score: float = 8.0,
    filter_type: str = "bm25",
    enable_filtering: bool = True,
    sync_tools: bool = False,
    custom_tools: Optional[List[Dict[str, Any]]] = None,
    custom_tool_handler: Optional[callable] = None,
    **provider_kwargs
) -> Dict[str, Any]:
    """
    Synchronous wrapper for chat_with_tools that uses asyncio.run() internally.
    
    Args:
        message: The user message/query
        provider: LLM provider ("anthropic", "openai", "gemini")
        model: Model name (auto-detected if not provided)
        observee_url: Direct Observee URL (client_id will be appended if missing)
        observee_api_key: Observee API key for authentication
        client_id: Observee client ID (defaults to env var)
        server_name: MCP server name (default: "observee")
        max_tools: Maximum number of tools to filter (default: 20)
        min_score: Minimum relevance score for tool filtering (default: 8.0)
        filter_type: Tool filter type ("bm25", "local_embedding", "cloud")
        enable_filtering: Whether to enable tool filtering (default: True)
        sync_tools: Whether to clear caches and sync tools (default: False)
        **provider_kwargs: Additional arguments for the LLM provider
    
    Returns:
        Dict containing:
        - content: The response text
        - tool_calls: List of tool calls made
        - tool_results: Results from tool executions
        - filtered_tools_count: Number of tools after filtering
        - filtered_tools: List of filtered tool names
        - used_filtering: Whether filtering was used
    
    Example:
        ```python
        from observee_agents import chat_with_tools
        
        result = chat_with_tools(
            message="Search for recent news about AI",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            observee_api_key="obs_your_key_here"
        )
        print(result["content"])
        ```
    """
    return asyncio.run(_chat_with_tools_async(
        message=message,
        provider=provider,
        model=model,
        observee_url=observee_url,
        observee_api_key=observee_api_key,
        client_id=client_id,
        server_name=server_name,
        max_tools=max_tools,
        min_score=min_score,
        filter_type=filter_type,
        enable_filtering=enable_filtering,
        sync_tools=sync_tools,
        custom_tools=custom_tools,
        custom_tool_handler=custom_tool_handler,
        **provider_kwargs
    ))

async def _chat_with_tools_stream_async(
    message: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee",
    max_tools: int = 20,
    min_score: float = 8.0,
    filter_type: str = "bm25",
    enable_filtering: bool = True,
    sync_tools: bool = False,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    custom_tools: Optional[List[Dict[str, Any]]] = None,
    custom_tool_handler: Optional[callable] = None,
    **provider_kwargs
):
    """
    Internal async function to handle streaming chat with tools
    """
    # Get or create session
    session = await _get_or_create_session(
        session_id=session_id,
        provider=provider,
        model=model,
        observee_url=observee_url,
        observee_api_key=observee_api_key,
        client_id=client_id,
        server_name=server_name,
        filter_type=filter_type,
        enable_filtering=enable_filtering,
        sync_tools=sync_tools,
        system_prompt=system_prompt,
        **provider_kwargs
    )
    
    # Stream the chat with tools using the session's agent
    async for chunk in session.agent.chat_with_tools_stream(
        message=message,
        max_tools=max_tools,
        min_score=min_score,
        custom_tools=custom_tools,
        custom_tool_handler=custom_tool_handler
    ):
        # Add session_id to metadata chunks
        if chunk.get("type") == "done":
            chunk["session_id"] = session.session_id
        elif chunk.get("type") == "metadata":
            chunk["session_id"] = session.session_id
        yield chunk

def chat_with_tools_stream(
    message: str,
    provider: str = "anthropic",
    model: Optional[str] = None,
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee",
    max_tools: int = 20,
    min_score: float = 8.0,
    filter_type: str = "bm25",
    enable_filtering: bool = True,
    sync_tools: bool = False,
    session_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    custom_tools: Optional[List[Dict[str, Any]]] = None,
    custom_tool_handler: Optional[callable] = None,
    **provider_kwargs
):
    """
    Stream chat with tools - returns an async generator for real-time responses.
    
    🆕 NEW: Now supports conversation history and custom system prompts!
    
    Args:
        message: The user message/query
        provider: LLM provider ("anthropic", "openai", "gemini")
        model: Model name (auto-detected if not provided)
        observee_url: Direct Observee URL (client_id will be appended if missing)
        observee_api_key: Observee API key for authentication
        client_id: Observee client ID (defaults to env var)
        server_name: MCP server name (default: "observee")
        max_tools: Maximum number of tools to filter (default: 20)
        min_score: Minimum relevance score for tool filtering (default: 8.0)
        filter_type: Tool filter type ("bm25", "local_embedding", "cloud")
        enable_filtering: Whether to enable tool filtering (default: True)
        sync_tools: Whether to clear caches and sync tools (default: False)
        session_id: Optional session ID for conversation history (auto-generated if not provided)
        system_prompt: Custom system prompt (uses default if not provided)
        **provider_kwargs: Additional arguments for the LLM provider
    
    Returns:
        Async generator yielding streaming chunks:
        - {'type': 'phase', 'phase': str} - Processing phase
        - {'type': 'content', 'content': str} - Text content chunks
        - {'type': 'tool_call', 'tool_call': dict} - Tool calls
        - {'type': 'tool_result', 'tool_name': str, 'result': str} - Tool results
        - {'type': 'final_content', 'content': str} - Final response chunks
        - {'type': 'done', 'final_response': dict} - Completion with full response
    
    Example:
        ```python
        import asyncio
        from observee_agents import chat_with_tools_stream
        
        async def main():
            async for chunk in chat_with_tools_stream(
                message="Search for recent news about AI",
                provider="openai",
                model="gpt-4o",
                observee_api_key="obs_your_key_here"
            ):
                if chunk["type"] == "content":
                    print(chunk["content"], end="", flush=True)
                elif chunk["type"] == "tool_result":
                    print(f"\\n[Tool {chunk['tool_name']} executed]")
                elif chunk["type"] == "done":
                    print("\\n[Complete]")
        
        asyncio.run(main())
        ```
    """
    return _chat_with_tools_stream_async(
        message=message,
        provider=provider,
        model=model,
        observee_url=observee_url,
        observee_api_key=observee_api_key,
        client_id=client_id,
        server_name=server_name,
        max_tools=max_tools,
        min_score=min_score,
        filter_type=filter_type,
        enable_filtering=enable_filtering,
        sync_tools=sync_tools,
        session_id=session_id,
        system_prompt=system_prompt,
        custom_tools=custom_tools,
        custom_tool_handler=custom_tool_handler,
        **provider_kwargs
    )

async def _list_tools_async(
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> List[Dict[str, Any]]:
    """
    Internal async function to list all available tools
    """
    # Get configuration
    config = _get_observee_config(observee_url, observee_api_key, client_id)
    
    # Use lightweight MCP client for faster tool listing
    async with MCPDirectClient(
        server_url=config["url"],
        auth_token=config["auth_token"],
        server_name=server_name
    ) as client:
        # Return all tools with their details
        return await client.list_tools()

def list_tools(
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> List[Dict[str, Any]]:
    """
    List all available tools from the MCP server.
    
    Args:
        observee_url: Direct Observee URL
        observee_api_key: Observee API key for authentication
        client_id: Observee client ID
        server_name: MCP server name (default: "observee")
    
    Returns:
        List of tools with name, description, and input schema
    
    Example:
        ```python
        from observee_agents import list_tools
        
        tools = list_tools(observee_api_key="obs_your_key_here")
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")
        ```
    """
    return asyncio.run(_list_tools_async(
        observee_url=observee_url,
        observee_api_key=observee_api_key,
        client_id=client_id,
        server_name=server_name
    ))

async def _filter_tools_async(
    query: str,
    max_tools: int = 10,
    min_score: float = 8.0,
    filter_type: str = "bm25",
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> List[Dict[str, Any]]:
    """
    Internal async function to filter tools based on a query
    """
    # Get configuration
    config = _get_observee_config(observee_url, observee_api_key, client_id)
    
    # Create and use agent with async context manager
    async with MCPAgent(
        provider="anthropic",  # Use minimal provider for tool filtering
        server_name=server_name,
        server_url=config["url"],
        auth_token=config["auth_token"],
        filter_type=filter_type,
        enable_filtering=True
    ) as agent:
        # Filter tools based on query
        filtered_tools = await agent.tool_filter.filter_tools(
            query, 
            max_tools=max_tools, 
            min_score=min_score
        )
        
        # Return filtered tools with their details and scores
        return [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema or {},
                "relevance_score": getattr(tool, 'score', 0.0)
            }
            for tool in filtered_tools
        ]

def filter_tools(
    query: str,
    max_tools: int = 10,
    min_score: float = 8.0,
    filter_type: str = "bm25",
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> List[Dict[str, Any]]:
    """
    Filter tools based on a query to find the most relevant ones.
    
    Args:
        query: Search query to filter tools
        max_tools: Maximum number of tools to return (default: 10)
        min_score: Minimum relevance score (default: 8.0)
        filter_type: Filter type ("bm25", "local_embedding", "cloud")
        observee_url: Direct Observee URL
        observee_api_key: Observee API key for authentication
        client_id: Observee client ID
        server_name: MCP server name (default: "observee")
    
    Returns:
        List of filtered tools with relevance scores
    
    Example:
        ```python
        from observee_agents import filter_tools
        
        tools = filter_tools(
            query="search YouTube videos",
            max_tools=5,
            observee_api_key="obs_your_key_here"
        )
        for tool in tools:
            print(f"- {tool['name']} (score: {tool['relevance_score']})")
        ```
    """
    return asyncio.run(_filter_tools_async(
        query=query,
        max_tools=max_tools,
        min_score=min_score,
        filter_type=filter_type,
        observee_url=observee_url,
        observee_api_key=observee_api_key,
        client_id=client_id,
        server_name=server_name
    ))

async def _get_tool_info_async(
    tool_name: str,
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> Optional[Dict[str, Any]]:
    """
    Internal async function to get detailed information about a specific tool
    """
    # Get configuration
    config = _get_observee_config(observee_url, observee_api_key, client_id)
    
    # Use lightweight MCP client for faster tool info retrieval
    async with MCPDirectClient(
        server_url=config["url"],
        auth_token=config["auth_token"],
        server_name=server_name
    ) as client:
        # Get the specific tool info
        return await client.get_tool_info(tool_name)

def get_tool_info(
    tool_name: str,
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific tool.
    
    Args:
        tool_name: Name of the tool to get info for
        observee_url: Direct Observee URL
        observee_api_key: Observee API key for authentication
        client_id: Observee client ID
        server_name: MCP server name (default: "observee")
    
    Returns:
        Tool information dict or None if tool not found
    
    Example:
        ```python
        from observee_agents import get_tool_info
        
        tool_info = get_tool_info(
            tool_name="youtube_get_transcript",
            observee_api_key="obs_your_key_here"
        )
        if tool_info:
            print(f"Tool: {tool_info['name']}")
            print(f"Description: {tool_info['description']}")
        ```
    """
    return asyncio.run(_get_tool_info_async(
        tool_name=tool_name,
        observee_url=observee_url,
        observee_api_key=observee_api_key,
        client_id=client_id,
        server_name=server_name
    ))

async def _execute_tool_async(
    tool_name: str,
    tool_input: Dict[str, Any],
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> Any:
    """
    Internal async function to execute a tool directly
    """
    # Get configuration
    config = _get_observee_config(observee_url, observee_api_key, client_id)
    
    # Use lightweight MCP client for faster tool execution
    async with MCPDirectClient(
        server_url=config["url"],
        auth_token=config["auth_token"],
        server_name=server_name
    ) as client:
        # Execute the tool
        return await client.execute_tool(tool_name, tool_input)

def execute_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    observee_url: Optional[str] = None,
    observee_api_key: Optional[str] = None,
    client_id: Optional[str] = None,
    server_name: str = "observee"
) -> Any:
    """
    Execute a specific tool with given input parameters.
    
    Args:
        tool_name: Name of the tool to execute
        tool_input: Input parameters for the tool
        observee_url: Direct Observee URL
        observee_api_key: Observee API key for authentication
        client_id: Observee client ID
        server_name: MCP server name (default: "observee")
    
    Returns:
        Tool execution result
    
    Example:
        ```python
        from observee_agents import execute_tool
        
        result = execute_tool(
            tool_name="youtube_get_transcript",
            tool_input={"video_url": "https://youtube.com/watch?v=..."},
            observee_api_key="obs_your_key_here"
        )
        print(result)
        ```
    """
    return asyncio.run(_execute_tool_async(
        tool_name=tool_name,
        tool_input=tool_input,
        observee_url=observee_url,
        observee_api_key=observee_api_key,
        client_id=client_id,
        server_name=server_name
    ))
