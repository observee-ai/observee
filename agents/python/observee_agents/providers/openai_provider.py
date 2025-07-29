"""
OpenAI GPT LLM provider with function calling support for MCP tools
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, AsyncIterator
from .base import LLMProvider

logger = logging.getLogger(__name__)

from openai import AsyncOpenAI
from dotenv import load_dotenv
        
load_dotenv()


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation using function calling for MCP tools"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: Optional API key (defaults to OPENAI_API_KEY env var)
            model: Model name (defaults to gpt-4.1)
        """
        
        # Configure API key
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        tools: List[Dict[str, Any]] = None,
        mcp_config: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response using OpenAI API with function calling
        
        Args:
            messages: Conversation history
            tools: Tool definitions in standard format
            mcp_config: MCP configuration (not used for OpenAI)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Dictionary with content, tool_calls, and raw_response
        """
        # Convert tools to OpenAI function format
        openai_tools = []
        if tools:
            logger.debug(f"Converting {len(tools)} tools to OpenAI format")
            for i, tool in enumerate(tools):
                logger.debug(f"Tool {i}: {tool}")
                # Handle both direct tool format and nested function format
                if "function" in tool:
                    # Already in OpenAI format
                    openai_tools.append(tool)
                else:
                    # Convert from standard format to OpenAI format
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "parameters": tool.get("inputSchema", {
                                "type": "object",
                                "properties": {},
                                "required": []
                            })
                        }
                    }
                    logger.debug(f"Converted tool: {openai_tool}")
                    openai_tools.append(openai_tool)
        
        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add tools if available
        if openai_tools:
            api_params["tools"] = openai_tools
            api_params["tool_choice"] = "auto"
        
        logger.debug(f"Calling OpenAI with model {self.model}")
        logger.debug(f"Tools provided: {len(openai_tools) if openai_tools else 0}")
        
        # Make API call
        try:
            response = await self.client.chat.completions.create(**api_params)
            
            # Extract message from response
            message = response.choices[0].message
            
            # Parse response
            result = {
                "content": message.content or "",
                "tool_calls": [],
                "raw_response": response
            }
            
            # Extract tool calls if present
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result["tool_calls"].append({
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        mcp_config: Dict[str, Any] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate streaming response using OpenAI API with proper tool call handling
        """
        # Convert tools to OpenAI function format
        openai_tools = []
        if tools:
            logger.debug(f"Converting {len(tools)} tools to OpenAI format (streaming)")
            for i, tool in enumerate(tools):
                logger.debug(f"Tool {i}: {tool}")
                # Handle both direct tool format and nested function format
                if "function" in tool:
                    # Already in OpenAI format
                    openai_tools.append(tool)
                else:
                    # Convert from standard format to OpenAI format
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "parameters": tool.get("inputSchema", {
                                "type": "object",
                                "properties": {},
                                "required": []
                            })
                        }
                    }
                    logger.debug(f"Converted tool: {openai_tool}")
                    openai_tools.append(openai_tool)
        
        # Extract generation parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 1000)
        
        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        # Add tools if available
        if openai_tools:
            api_params["tools"] = openai_tools
            api_params["tool_choice"] = "auto"
        
        logger.debug(f"Calling OpenAI streaming with model {self.model}")
        logger.debug(f"Tools provided: {len(openai_tools) if openai_tools else 0}")
        
        # Make streaming API call
        try:
            stream = await self.client.chat.completions.create(**api_params)
            
            # Track accumulated data for tool calls
            accumulated_content = ""
            tool_calls = []
            accumulated_tool_call = {}
            
            async for chunk in stream:
                logger.debug(f"OpenAI chunk: {chunk}")
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    # Handle content
                    if hasattr(delta, 'content') and delta.content:
                        accumulated_content += delta.content
                        yield {
                            "type": "content",
                            "content": delta.content
                        }
                    
                    # Handle tool calls
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        logger.debug(f"Tool calls in delta: {delta.tool_calls}")
                        for tool_call in delta.tool_calls:
                            logger.debug(f"Individual tool call: {tool_call}")
                            
                            # Get the tool call index to track which tool call this chunk belongs to
                            tool_call_index = getattr(tool_call, 'index', 0)
                            tool_call_id = getattr(tool_call, 'id', None)
                            
                            # Initialize tool call if we see an id (first chunk for this tool call)
                            if tool_call_id:
                                accumulated_tool_call[tool_call_index] = {
                                    "id": tool_call_id,
                                    "type": "function",
                                    "function": {
                                        "name": "",
                                        "arguments": ""
                                    }
                                }
                            
                            # Make sure we have an entry for this tool call index
                            if tool_call_index not in accumulated_tool_call:
                                # Create a placeholder if we don't have the id yet
                                accumulated_tool_call[tool_call_index] = {
                                    "id": f"call_{tool_call_index}",  # Fallback id
                                    "type": "function",
                                    "function": {
                                        "name": "",
                                        "arguments": ""
                                    }
                                }
                            
                            # Accumulate function name and arguments
                            if hasattr(tool_call, 'function'):
                                func = tool_call.function
                                if hasattr(func, 'name') and func.name:
                                    accumulated_tool_call[tool_call_index]["function"]["name"] = func.name
                                if hasattr(func, 'arguments') and func.arguments:
                                    accumulated_tool_call[tool_call_index]["function"]["arguments"] += func.arguments
                
                # Check if this is the final chunk
                if chunk.choices[0].finish_reason:
                    # Yield any completed tool calls
                    for tool_call in accumulated_tool_call.values():
                        yield {
                            "type": "tool_call",
                            "tool_call": tool_call
                        }
                    
                    # Yield completion
                    yield {
                        "type": "done",
                        "final_response": {
                            "content": accumulated_content,
                            "tool_calls": list(accumulated_tool_call.values()),
                            "raw_response": chunk
                        }
                    }
                    break
                    
        except Exception as e:
            logger.error(f"Error calling OpenAI streaming API: {e}")
            raise