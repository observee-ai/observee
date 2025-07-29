"""
Base LLM provider interface
"""

from typing import List, Dict, Any, Protocol, runtime_checkable, AsyncIterator
from abc import abstractmethod


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers to ensure compatibility"""
    
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None, mcp_config: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            messages: Conversation history
            tools: Optional list of available tools
            mcp_config: Optional MCP server configuration for native MCP support
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Dict with 'content', 'tool_calls', and 'raw_response'
        """
        ...
    
    async def generate_stream(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None, mcp_config: Dict[str, Any] = None, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate a streaming response from the LLM.
        
        Args:
            messages: Conversation history
            tools: Optional list of available tools
            mcp_config: Optional MCP server configuration for native MCP support
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Yields:
            Dict with 'type' and relevant data:
            - {'type': 'content', 'content': str} for text chunks
            - {'type': 'tool_call', 'tool_call': dict} for tool calls
            - {'type': 'done', 'final_response': dict} for completion
        """
        # Default implementation: call generate and yield the result
        result = await self.generate(messages, tools, mcp_config, **kwargs)
        
        # Yield content if present
        if result.get("content"):
            yield {
                "type": "content",
                "content": result["content"]
            }
        
        # Yield tool calls if present
        for tool_call in result.get("tool_calls", []):
            yield {
                "type": "tool_call",
                "tool_call": tool_call
            }
        
        # Yield completion
        yield {
            "type": "done",
            "final_response": result
        }