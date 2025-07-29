"""
Anthropic Claude LLM provider
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from .base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        from dotenv import load_dotenv
        
        load_dotenv()
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
    
    async def generate(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None, mcp_config: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Generate response using Anthropic API with native MCP support"""
        # Extract parameters
        max_tokens = kwargs.get("max_tokens", 1000)
        temperature = kwargs.get("temperature", 0.7)
        
        # Extract system message if present
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Use native MCP if config provided
        if mcp_config:
            create_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                "mcp_servers": [mcp_config],
                "extra_headers": {
                    "anthropic-beta": "mcp-client-2025-04-04"
                }
            }
            if system_message:
                create_params["system"] = system_message
            
            response = self.client.beta.messages.create(**create_params)
        # Fallback to standard tool calling
        elif tools:
            # Convert tools to Anthropic format
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}})
                })
            
            logger.debug(f"Converting {len(tools)} tools to Anthropic format")
            for i, tool in enumerate(anthropic_tools):
                logger.debug(f"Anthropic tool {i}: {tool}")
            
            create_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                "tools": anthropic_tools,
                "temperature": temperature
            }
            if system_message:
                create_params["system"] = system_message
            
            response = self.client.messages.create(**create_params)
        else:
            create_params = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                "temperature": temperature
            }
            if system_message:
                create_params["system"] = system_message
            
            response = self.client.messages.create(**create_params)
        
        # Extract content and tool calls
        content = ""
        tool_calls = []
        
        if hasattr(response, 'content') and response.content:
            if isinstance(response.content, list):
                for item in response.content:
                    if hasattr(item, 'text'):
                        content += item.text
                    elif hasattr(item, 'type') and item.type == 'tool_use':
                        # Extract tool call information
                        tool_call = {
                            "id": item.id,
                            "type": "function",
                            "function": {
                                "name": item.name,
                                "arguments": json.dumps(item.input) if hasattr(item, 'input') else "{}"
                            }
                        }
                        tool_calls.append(tool_call)
            else:
                content = str(response.content)
        
        return {
            "content": content,
            "tool_calls": tool_calls,
            "raw_response": response
        }
    
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        mcp_config: Dict[str, Any] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate streaming response using Anthropic API with native MCP support
        """
        # Extract parameters
        max_tokens = kwargs.get("max_tokens", 1000)
        temperature = kwargs.get("temperature", 0.7)
        
        # Extract system message if present
        system_message = None
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        logger.debug(f"Calling Anthropic streaming with model {self.model}")
        logger.debug(f"MCP config provided: {mcp_config is not None}")
        logger.debug(f"Tools provided: {len(tools) if tools else 0}")
        
        try:
            # Use native MCP if config provided
            if mcp_config:
                logger.info(f"Using native MCP with config: {mcp_config}")
                create_params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": anthropic_messages,
                    "mcp_servers": [mcp_config],
                    "extra_headers": {
                        "anthropic-beta": "mcp-client-2025-04-04"
                    },
                    "stream": True
                }
                if system_message:
                    create_params["system"] = system_message
                
                stream = self.client.beta.messages.create(**create_params)
            # Fallback to standard tool calling
            elif tools:
                # Convert tools to Anthropic format
                logger.info(f"Using standard tool calling with {len(tools)} tools")
                anthropic_tools = []
                for tool in tools:
                    anthropic_tools.append({
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "input_schema": tool.get("inputSchema", {"type": "object", "properties": {}})
                    })
                
                logger.debug(f"Converting {len(tools)} tools to Anthropic format")
                for i, tool in enumerate(anthropic_tools):
                    logger.debug(f"Anthropic tool {i}: {tool}")
                
                create_params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": anthropic_messages,
                    "tools": anthropic_tools,
                    "temperature": temperature,
                    "stream": True
                }
                if system_message:
                    create_params["system"] = system_message
                
                stream = self.client.messages.create(**create_params)
            else:
                create_params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": anthropic_messages,
                    "temperature": temperature,
                    "stream": True
                }
                if system_message:
                    create_params["system"] = system_message
                
                stream = self.client.messages.create(**create_params)
            
            # Track accumulated data
            accumulated_content = ""
            tool_calls = []
            
            # Process the streaming response
            current_tool_index = -1
            
            for chunk in stream:
                if chunk.type == "content_block_delta":
                    if chunk.delta.type == "text_delta":
                        text_chunk = chunk.delta.text
                        accumulated_content += text_chunk
                        yield {
                            "type": "content",
                            "content": text_chunk
                        }
                    elif chunk.delta.type == "input_json_delta":
                        # Handle tool use input delta
                        if tool_calls and current_tool_index >= 0:
                            tool_calls[current_tool_index]["function"]["arguments"] += chunk.delta.partial_json
                elif chunk.type == "content_block_start":
                    # Handle tool use blocks
                    if hasattr(chunk.content_block, 'type') and chunk.content_block.type == "tool_use":
                        tool_call = {
                            "id": chunk.content_block.id,
                            "type": "function",
                            "function": {
                                "name": chunk.content_block.name,
                                "arguments": ""
                            }
                        }
                        tool_calls.append(tool_call)
                        current_tool_index = len(tool_calls) - 1
                elif chunk.type == "content_block_stop":
                    # When a content block (like a tool use) is complete, yield it
                    if current_tool_index >= 0 and current_tool_index < len(tool_calls):
                        yield {
                            "type": "tool_call",
                            "tool_call": tool_calls[current_tool_index]
                        }
                elif chunk.type == "message_stop":
                    # Yield completion
                    yield {
                        "type": "done",
                        "final_response": {
                            "content": accumulated_content,
                            "tool_calls": tool_calls,
                            "raw_response": chunk
                        }
                    }
                    break
                    
        except Exception as e:
            logger.error(f"Error calling Anthropic streaming API: {e}")
            raise