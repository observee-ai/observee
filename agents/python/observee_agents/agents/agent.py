"""
Simplified MCP agent using modular components
"""

from typing import List, Dict, Any, Optional, Union, AsyncIterator
from fastmcp import Client
from dotenv import load_dotenv
import logging

from .base import BaseAgent, AgentResponse
from .conversation import ConversationManager
from .tool_handler import ToolHandler
from .streaming import StreamingHandler
from ..providers.base import LLMProvider
from ..utils.tool_converter import clear_tool_cache

logger = logging.getLogger(__name__)


class MCPAgent(BaseAgent):
    """Modular MCP agent with clean separation of concerns"""
    
    def __init__(
        self,
        provider: Union[str, LLMProvider] = "anthropic",
        server_name: str = "observee",
        model: Optional[str] = None,
        server_url: str = None,
        sync_tools: bool = True,
        filter_type: Optional[str] = None,
        enable_filtering: bool = True,
        auth_token: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **provider_kwargs
    ):
        """
        Initialize MCP Agent
        
        Args:
            provider: LLM provider name or instance
            server_name: Name of the MCP server
            model: Model to use
            server_url: URL of the MCP server
            sync_tools: Whether to sync tools with cloud
            filter_type: Type of filter to use
            enable_filtering: Whether to enable tool filtering
            auth_token: Authentication token
            system_prompt: Custom system prompt
            **provider_kwargs: Additional provider arguments
        """
        load_dotenv()
        
        # Validate server URL
        if not server_url:
            raise ValueError("server_url is required. Please provide the MCP server URL.")
        
        self.server_name = server_name
        self.server_url = server_url
        self.auth_token = auth_token
        self.enable_filtering = enable_filtering
        
        # Initialize MCP client
        self.mcp = self._create_mcp_client()
        
        # Initialize provider
        self.provider, self.provider_name = self._initialize_provider(
            provider, model, **provider_kwargs
        )
        self.model = model or self._get_default_model()
        
        # Initialize components
        self.conversation = ConversationManager(system_prompt)
        self.tool_handler = ToolHandler(
            self.mcp,
            enable_filtering=enable_filtering,
            filter_type=filter_type,
            sync_tools=sync_tools,
            server_name=server_name,
            server_url=server_url
        )
        self.streaming = StreamingHandler(self.tool_handler)
        
        # Clear tool cache on init
        clear_tool_cache()
        
        # Context manager state
        self._client_context = None
    
    def _create_mcp_client(self) -> Client:
        """Create and configure MCP client"""
        config = {
            "mcpServers": {
                self.server_name: {"url": self.server_url}
            }
        }
        
        # Add auth headers if provided
        if self.auth_token:
            config["mcpServers"][self.server_name]["headers"] = {
                "Authorization": f"Bearer {self.auth_token}"
            }
        
        return Client(config)
    
    def _initialize_provider(
        self, 
        provider: Union[str, LLMProvider], 
        model: Optional[str], 
        **kwargs
    ) -> tuple[LLMProvider, str]:
        """Initialize the LLM provider"""
        if isinstance(provider, LLMProvider):
            provider_name = provider.__class__.__name__
            return provider, provider_name
        
        # String provider name - load from registry
        from ..providers import PROVIDERS
        
        provider_lower = provider.lower()
        if provider_lower not in PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(PROVIDERS.keys())}")
        
        provider_class = PROVIDERS[provider_lower]
        provider_args = kwargs.copy()
        if model:
            provider_args['model'] = model
        
        provider_instance = provider_class(**provider_args)
        
        # Set MCP client for LangChain provider
        if hasattr(provider_instance, 'set_mcp_client'):
            provider_instance.set_mcp_client(self.mcp)
        
        return provider_instance, provider_lower
    
    def _get_default_model(self) -> str:
        """Get default model based on provider"""
        defaults = {
            "anthropic": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "gemini": "gemini-2.5-pro",
            "groq": "moonshotai/kimi-k2-instruct"
        }
        return defaults.get(self.provider_name, "default")
    
    async def __aenter__(self):
        """Enter async context"""
        self._client_context = await self.mcp.__aenter__()
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context"""
        if self._client_context:
            await self.mcp.__aexit__(exc_type, exc_val, exc_tb)
    
    async def initialize(self):
        """Initialize the MCP connection and load tools"""
        await self.tool_handler.load_tools()
    
    async def chat(
        self,
        message: str,
        max_tools: int = 20,
        min_score: float = 8.0,
        context: Optional[Dict[str, Any]] = None,
        custom_tools: Optional[List[Dict[str, Any]]] = None,
        expand_by_server: bool = False
    ) -> Dict[str, Any]:
        """Chat with the agent using filtered tools
        
        Args:
            message: User message
            max_tools: Maximum number of tools to use
            min_score: Minimum score for tool filtering
            context: Optional context for filtering
            custom_tools: Optional custom tools to add
            expand_by_server: If True, include all tools from same server when a tool is selected
        """
        # Add user message to history
        self.conversation.add_message("user", message)
        
        # Get appropriate tools
        tools_to_use, mcp_config = await self._prepare_tools_and_config(
            message, max_tools, min_score, context, custom_tools, expand_by_server
        )
        
        # Call provider
        response = await self._call_provider(tools_to_use, mcp_config)
        
        # Parse response
        content = response.get("content", "")
        tool_calls = self.tool_handler.parse_tool_calls(response)
        
        # Add assistant response to history
        self.conversation.add_message("assistant", content)
        
        # Build response
        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            filtered_tools_count=len(tools_to_use) if tools_to_use else 0,
            filtered_tools=[t["name"] for t in (tools_to_use or [])],
            used_filtering=self.enable_filtering
        ).to_dict()
    
    async def chat_stream(
        self,
        message: str,
        max_tools: int = 20,
        min_score: float = 8.0,
        custom_tools: Optional[List[Dict[str, Any]]] = None,
        expand_by_server: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat response with filtered tools
        
        Args:
            message: User message
            max_tools: Maximum number of tools to use
            min_score: Minimum score for tool filtering
            custom_tools: Optional custom tools to add
            expand_by_server: If True, include all tools from same server when a tool is selected
        """
        # Add user message to history
        self.conversation.add_message("user", message)
        
        # Get appropriate tools
        tools_to_use, mcp_config = await self._prepare_tools_and_config(
            message, max_tools, min_score, None, custom_tools, expand_by_server
        )
        
        # Stream from provider
        messages = self.conversation.get_messages_with_system()
        
        accumulated_content = ""
        tool_calls = []
        
        async for chunk in self.provider.generate_stream(
            messages=messages,
            tools=tools_to_use,
            mcp_config=mcp_config
        ):
            if chunk["type"] == "content":
                accumulated_content += chunk["content"]
                yield chunk
            elif chunk["type"] == "tool_call":
                tool_calls.append(chunk["tool_call"])
                yield chunk
            elif chunk["type"] == "done":
                # Add assistant response to history
                self.conversation.add_message("assistant", accumulated_content)
                
                # Yield final metadata
                yield {
                    "type": "metadata",
                    "filtered_tools_count": len(tools_to_use) if tools_to_use else 0,
                    "filtered_tools": [t["name"] for t in (tools_to_use or [])],
                    "used_filtering": self.enable_filtering,
                    "tool_calls": tool_calls
                }
                break
    
    async def chat_with_tools(
        self,
        message: str,
        max_tools: int = 20,
        min_score: float = 8.0,
        custom_tools: Optional[List[Dict[str, Any]]] = None,
        custom_tool_handler: Optional[callable] = None,
        expand_by_server: bool = False
    ) -> Dict[str, Any]:
        """Complete chat flow with tool execution
        
        Args:
            message: User message
            max_tools: Maximum number of tools to use
            min_score: Minimum score for tool filtering
            custom_tools: Optional custom tools to add
            custom_tool_handler: Optional handler for custom tools
            expand_by_server: If True, include all tools from same server when a tool is selected
        """
        # Get initial response
        initial_response = await self.chat(
            message, 
            max_tools=max_tools,
            min_score=min_score,
            custom_tools=custom_tools,
            expand_by_server=expand_by_server
        )
        
        # If no tool calls, return as is
        if not initial_response['tool_calls']:
            return initial_response
        
        # Execute tools
        _, custom_tool_names = self.tool_handler.prepare_tools_for_provider([], custom_tools)
        tool_results = []
        
        async for result in self.streaming.handle_tool_execution_stream(
            initial_response['tool_calls'],
            custom_tool_names,
            custom_tool_handler
        ):
            if result["type"] == "tool_result":
                tool_results.append({
                    'tool': result['tool_name'],
                    'result': result['result']
                })
            elif result["type"] == "tool_error":
                tool_results.append({
                    'tool': result['tool_name'],
                    'error': result['error']
                })
        
        # Format and add tool results
        tool_results_text = self.streaming.format_tool_results(tool_results)
        self.conversation.add_message("user", tool_results_text)
        
        # Get final response
        final_response = await self.provider.generate(
            messages=self.conversation.get_messages_with_system()
        )
        
        final_content = final_response.get("content", "")
        self.conversation.add_message("assistant", final_content)
        
        return {
            "content": final_content,
            "initial_response": initial_response['content'],
            "tool_calls": initial_response['tool_calls'],
            "tool_results": tool_results,
            "filtered_tools_count": initial_response['filtered_tools_count'],
            "filtered_tools": initial_response['filtered_tools'],
            "used_filtering": initial_response['used_filtering']
        }
    
    async def chat_with_tools_stream(
        self,
        message: str,
        max_tools: int = 20,
        min_score: float = 8.0,
        custom_tools: Optional[List[Dict[str, Any]]] = None,
        custom_tool_handler: Optional[callable] = None,
        expand_by_server: bool = False
    ) -> AsyncIterator[Dict[str, Any]]:
        """Complete streaming chat flow with tool execution
        
        Args:
            message: User message
            max_tools: Maximum number of tools to use
            min_score: Minimum score for tool filtering
            custom_tools: Optional custom tools to add
            custom_tool_handler: Optional handler for custom tools
            expand_by_server: If True, include all tools from same server when a tool is selected
        """
        initial_tool_calls = []
        accumulated_content = ""
        metadata = {}
        
        # Stream initial response
        async for chunk in self.chat_stream(
            message,
            max_tools=max_tools,
            min_score=min_score,
            custom_tools=custom_tools,
            expand_by_server=expand_by_server
        ):
            if chunk["type"] == "content":
                accumulated_content += chunk["content"]
                yield chunk
            elif chunk["type"] == "tool_call":
                initial_tool_calls.append(chunk["tool_call"])
                chunk["initial_content"] = accumulated_content
                yield chunk
            elif chunk["type"] == "metadata":
                metadata = chunk
                break
        
        # If no tool calls, we're done
        if not initial_tool_calls:
            yield {
                "type": "done",
                "final_response": {
                    "content": accumulated_content,
                    "tool_calls": [],
                    "tool_results": [],
                    **metadata
                }
            }
            return
        
        # Execute tools
        _, custom_tool_names = self.tool_handler.prepare_tools_for_provider([], custom_tools)
        tool_results = []
        
        async for result in self.streaming.handle_tool_execution_stream(
            initial_tool_calls,
            custom_tool_names,
            custom_tool_handler
        ):
            yield result
            if result["type"] == "tool_result":
                tool_results.append({
                    'tool': result['tool_name'],
                    'result': result['result']
                })
            elif result["type"] == "tool_error":
                tool_results.append({
                    'tool': result['tool_name'],
                    'error': result['error']
                })
        
        # Format and add tool results
        tool_results_text = self.streaming.format_tool_results(tool_results)
        self.conversation.add_message("user", tool_results_text)
        
        # Stream final response - need to include tools so LLM can make additional calls if needed
        # Keep executing tools in a loop until no more tool calls are made
        all_tool_calls = initial_tool_calls.copy()
        all_tool_results = tool_results.copy()
        
        max_rounds = 10  # Prevent infinite loops
        for _ in range(max_rounds):
            final_content = ""
            additional_tool_calls = []
            messages = self.conversation.get_messages_with_system()
            
            # Get the same tools configuration that was used initially
            tools_to_use, mcp_config = await self._prepare_tools_and_config(
                message, max_tools, min_score, None, custom_tools, expand_by_server
            )
            
            async for chunk in self.provider.generate_stream(
                messages=messages,
                tools=tools_to_use,
                mcp_config=mcp_config
            ):
                if chunk["type"] == "content":
                    final_content += chunk["content"]
                    yield {
                        "type": "final_content",
                        "content": chunk["content"]
                    }
                elif chunk["type"] == "tool_call":
                    # LLM wants to make another tool call
                    additional_tool_calls.append(chunk["tool_call"])
                    yield chunk
                elif chunk["type"] == "done":
                    break
            
            # Add the response to conversation (only if there's content or tool calls)
            # We need to track the assistant's message even if it only contains tool calls
            if final_content or additional_tool_calls:
                self.conversation.add_message("assistant", final_content if final_content else "[Tool calls executed]")
            
            # If no more tool calls, we're done
            if not additional_tool_calls:
                yield {
                    "type": "done",
                    "final_response": {
                        "content": final_content,
                        "initial_response": accumulated_content,
                        "tool_calls": all_tool_calls,
                        "tool_results": all_tool_results,
                        **metadata
                    }
                }
                return  # Use return instead of break to ensure we exit the function
            
            # Execute the additional tools
            all_tool_calls.extend(additional_tool_calls)
            
            async for result in self.streaming.handle_tool_execution_stream(
                additional_tool_calls,
                custom_tool_names,
                custom_tool_handler
            ):
                yield result
                if result["type"] == "tool_result":
                    all_tool_results.append({
                        'tool': result['tool_name'],
                        'result': result['result']
                    })
                elif result["type"] == "tool_error":
                    all_tool_results.append({
                        'tool': result['tool_name'],
                        'error': result['error']
                    })
            
            # Format and add tool results to conversation
            tool_results_text = self.streaming.format_tool_results(all_tool_results[-len(additional_tool_calls):])
            self.conversation.add_message("user", tool_results_text)
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool call through MCP"""
        return await self.tool_handler.execute_tool(tool_name, tool_input)
    
    def reset_conversation(self):
        """Reset the conversation history"""
        self.conversation.reset()
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history"""
        return self.conversation.get_history()
    
    async def _prepare_tools_and_config(
        self,
        message: str,
        max_tools: int,
        min_score: float,
        context: Optional[Dict[str, Any]],
        custom_tools: Optional[List[Dict[str, Any]]],
        expand_by_server: bool = False
    ) -> tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """Prepare tools and MCP config based on filtering settings
        
        Args:
            message: User message
            max_tools: Maximum number of tools
            min_score: Minimum score for filtering
            context: Optional context
            custom_tools: Optional custom tools
            expand_by_server: If True, include all tools from same server
        """
        if self.enable_filtering:
            # Use filtering with optional server expansion
            filtered_tools, _ = await self.tool_handler.filter_tools(
                message, max_tools, min_score, context, expand_by_server
            )
            
            # Convert filtered tools
            original_tools = self.tool_handler.get_original_tools(filtered_tools)
            tools, _ = self.tool_handler.prepare_tools_for_provider(
                original_tools, custom_tools
            )
            return tools, None
        else:
            # No filtering - use native MCP or all tools
            if self._supports_native_mcp():
                return None, self._get_mcp_config()
            else:
                tools, _ = self.tool_handler.prepare_tools_for_provider(
                    self.tool_handler.all_tools, custom_tools
                )
                return tools, None
    
    
    def _supports_native_mcp(self) -> bool:
        """Check if provider supports native MCP"""
        return self.provider_name in ["anthropic", "gemini"] and not self.enable_filtering
    
    def _get_mcp_config(self) -> Dict[str, Any]:
        """Get MCP configuration for native support"""
        if self.provider_name == "anthropic":
            config = {
                "type": "url",
                "url": self.server_url,
                "name": self.server_name
            }
            if self.auth_token:
                config["authorization_token"] = self.auth_token
            return config
        elif self.provider_name == "gemini":
            return {"session": self.mcp.session}
        return None
    
    async def _call_provider(
        self,
        tools: Optional[List[Dict[str, Any]]],
        mcp_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call the LLM provider with appropriate configuration"""
        messages = self.conversation.get_messages_with_system()
        
        return await self.provider.generate(
            messages=messages,
            tools=tools,
            mcp_config=mcp_config
        )
    
