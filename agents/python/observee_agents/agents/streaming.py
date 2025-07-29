"""
Streaming response handling
"""

from typing import Dict, Any, List, Optional, AsyncIterator, Callable
import logging
import json

logger = logging.getLogger(__name__)


class StreamingHandler:
    """Handles streaming responses from LLM providers"""
    
    def __init__(self, tool_handler=None):
        """
        Initialize streaming handler
        
        Args:
            tool_handler: Optional tool handler for executing tools
        """
        self.tool_handler = tool_handler
    
    async def handle_streaming_response(
        self,
        stream_generator: AsyncIterator[Dict[str, Any]],
        accumulate_content: bool = True
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Handle a streaming response and accumulate results
        
        Args:
            stream_generator: Async generator yielding chunks
            accumulate_content: Whether to accumulate content
            
        Yields:
            Chunks from the stream and final accumulated response
        """
        accumulated_content = ""
        tool_calls = []
        metadata = {}
        
        async for chunk in stream_generator:
            if chunk["type"] == "content":
                if accumulate_content:
                    accumulated_content += chunk["content"]
                yield chunk
            
            elif chunk["type"] == "tool_call":
                tool_calls.append(chunk["tool_call"])
                yield chunk
            
            elif chunk["type"] == "metadata":
                metadata = chunk
                break
            
            elif chunk["type"] == "done":
                break
        
        # Yield final accumulated response
        yield {
            "type": "final",
            "content": accumulated_content,
            "tool_calls": tool_calls,
            **metadata
        }
    
    async def handle_tool_execution_stream(
        self,
        initial_tool_calls: List[Dict[str, Any]],
        custom_tool_names: List[str],
        custom_tool_handler: Optional[Callable] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute tools and yield results as a stream
        
        Args:
            initial_tool_calls: List of tool calls to execute
            custom_tool_names: Names of custom tools
            custom_tool_handler: Handler for custom tools
            
        Yields:
            Tool execution results and errors
        """
        tool_results = []
        
        for tool_call in initial_tool_calls:
            try:
                # Parse tool call
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                
                # Skip empty tool names
                if not tool_name:
                    continue
                
                # Parse arguments
                arguments = function_info.get("arguments", "{}")
                if isinstance(arguments, str):
                    try:
                        args = json.loads(arguments) if arguments.strip() else {}
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = arguments if arguments else {}
                
                # Execute tool
                if tool_name in custom_tool_names and custom_tool_handler:
                    # Execute custom tool
                    result = await custom_tool_handler(tool_name, args)
                else:
                    # Execute MCP tool
                    if self.tool_handler:
                        result = await self.tool_handler.execute_tool(tool_name, args)
                    else:
                        raise ValueError("No tool handler available for MCP tools")
                
                tool_results.append({
                    'tool': tool_name,
                    'result': str(result)
                })
                
                yield {
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": str(result)
                }
                
            except Exception as e:
                tool_results.append({
                    'tool': tool_name,
                    'error': str(e)
                })
                
                yield {
                    "type": "tool_error",
                    "tool_name": tool_name,
                    "error": str(e)
                }
    
    def format_tool_results(self, tool_results: List[Dict[str, Any]]) -> str:
        """Format tool results for the assistant"""
        return "\n\n".join([
            f"Tool: {r['tool']}\nResult: {r.get('result', r.get('error', 'No result'))}"
            for r in tool_results
        ])