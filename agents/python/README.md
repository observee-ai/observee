# Observee Agents

A Python SDK for seamless integration of MCP (Model Context Protocol) tools with multiple LLM providers including Anthropic Claude, OpenAI GPT, and Google Gemini.

**Configure as many MCP servers/tools as you need at [observee.ai](https://observee.ai)**

## Features

- 🤖 **Multi-Provider Support**: Works with Anthropic, OpenAI, and Gemini
- 🔧 **Smart Tool Filtering**: BM25, local embeddings, and cloud-based filtering
- ⚡ **Fast Performance**: Intelligent caching and optimization
- 🔑 **Flexible Authentication**: URL-based or API key authentication
- 🔐 **OAuth Integration**: Built-in authentication flows for Gmail, Slack, Notion, and 15+ services
- 🎯 **Easy Integration**: Simple sync/async API
- 📡 **Streaming Support**: Real-time streaming responses for Anthropic, OpenAI, and Gemini
- 🗨️ **Conversation History**: Persistent memory across chat sessions
- 🎯 **Custom System Prompts**: Personalized AI behavior and expertise
- 📦 **Pip Installable**: Easy installation and distribution

## Installation

```bash
# Basic installation
pip install observee-agents

# With optional dependencies
pip install observee-agents[embedding,cloud]

# Development installation
pip install observee-agents[dev]
```

## Quick Start

### Simple Synchronous Usage (Recommended)

```python
from observee_agents import chat_with_tools

result = chat_with_tools(
    message="Search for recent news about AI developments",
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    observee_api_key="obs_your_key_here"
)

print("Response:", result["content"])
print("Tools used:", len(result["tool_calls"]))
```

### Explore Available Tools

```python
from observee_agents import list_tools, get_tool_info, filter_tools

# List all available tools
tools = list_tools(observee_api_key="obs_your_key_here")
print(f"Found {len(tools)} tools:")
for tool in tools[:5]:  # Show first 5
    print(f"- {tool['name']}: {tool['description']}")

# Get detailed info about a specific tool
tool_info = get_tool_info(
    tool_name="youtube_get_transcript",
    observee_api_key="obs_your_key_here"
)
if tool_info:
    print(f"Tool: {tool_info['name']}")
    print(f"Description: {tool_info['description']}")

# Find relevant tools for a task
relevant_tools = filter_tools(
    query="search YouTube videos",
    max_tools=3,
    observee_api_key="obs_your_key_here"
)
for tool in relevant_tools:
    print(f"- {tool['name']} (relevance: {tool['relevance_score']})")
```

### Execute Tools Directly

```python
from observee_agents import execute_tool

# Execute a tool directly without LLM
result = execute_tool(
    tool_name="youtube_get_transcript", 
    tool_input={"video_url": "https://youtube.com/watch?v=dQw4w9WgXcQ"},
    observee_api_key="obs_your_key_here"
)
print(result)
```

### Custom Tools

You can extend the SDK with your own custom tools alongside the MCP tools:

```python
from observee_agents import chat_with_tools_stream
import asyncio

# Define custom tool handler
async def custom_tool_handler(tool_name: str, tool_input: dict) -> str:
    """Handle custom tool executions"""
    if tool_name == "add_numbers":
        return str(tool_input.get("a", 0) + tool_input.get("b", 0))
    elif tool_name == "multiply_numbers":
        return str(tool_input.get("a", 0) * tool_input.get("b", 0))
    elif tool_name == "get_time":
        from datetime import datetime
        return datetime.now().strftime("%I:%M %p")
    else:
        return f"Unknown tool: {tool_name}"

# Define custom tools in OpenAI format
custom_tools = [
    {
        "type": "function",
        "function": {
            "name": "add_numbers",
            "description": "Add two numbers together",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

# Use custom tools with MCP tools
async def custom_example():
    async for chunk in chat_with_tools_stream(
        message="What's 5 + 3? Also, what time is it?",
        provider="openai",
        custom_tools=custom_tools,
        custom_tool_handler=custom_tool_handler,
        observee_api_key="obs_your_key_here"
    ):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_result":
            print(f"\n🔧 [Tool: {chunk['tool_name']} = {chunk['result']}]")

asyncio.run(custom_example())
```

Custom tools work seamlessly with all providers (Anthropic, OpenAI, Gemini) and can be combined with MCP tools for enhanced functionality.

### Streaming Responses

```python
import asyncio
from observee_agents import chat_with_tools_stream

async def stream_example():
    async for chunk in chat_with_tools_stream(
        message="What's the weather like today?",
        provider="openai",
        observee_api_key="obs_your_key_here"
    ):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
        elif chunk["type"] == "tool_result":
            print(f"\n[Tool executed: {chunk['tool_name']}]")

asyncio.run(stream_example())
```

### 🆕 Conversational AI with Memory

```python
import asyncio
from observee_agents import chat_with_tools_stream, get_conversation_history

async def conversation_example():
    # Create a specialized assistant with conversation memory
    session_id = "my_email_assistant"
    custom_prompt = "You are a professional email assistant. Be concise and helpful."
    
    # First message with custom system prompt
    async for chunk in chat_with_tools_stream(
        message="Search for emails about meetings",
        provider="anthropic",
        session_id=session_id,  # 🆕 Enables conversation memory
        system_prompt=custom_prompt,  # 🆕 Custom AI behavior
        observee_api_key="obs_your_key_here"
    ):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
    
    print("\n" + "="*40 + "\n")
    
    # Follow-up - remembers previous context!
    async for chunk in chat_with_tools_stream(
        message="What was the subject of the first meeting?",
        session_id=session_id,  # Same session = memory!
        observee_api_key="obs_your_key_here"
    ):
        if chunk["type"] == "content":
            print(chunk["content"], end="", flush=True)
    
    # Check conversation history
    history = get_conversation_history(session_id)
    print(f"\n📊 Conversation has {len(history)} messages")

asyncio.run(conversation_example())
```

### Advanced Async Usage

```python
import asyncio
from observee_agents import MCPAgent

async def advanced_example():
    async with MCPAgent(
        provider="anthropic",
        server_url="wss://mcp.observee.ai/mcp?client_id=your_id",
        auth_token="obs_your_key_here"
    ) as agent:
        result = await agent.chat_with_tools(
            message="What tools do you have access to?"
        )
        return result

result = asyncio.run(advanced_example())
print(result["content"])
```

### OAuth Authentication

The SDK includes built-in OAuth flows for authenticating with various services:

```python
from observee_agents import call_mcpauth_login, get_available_servers

# Get list of supported authentication servers
servers = get_available_servers()
print(f"Available servers: {servers['supported_servers']}")

# Start authentication flow for Gmail
response = call_mcpauth_login(auth_server="gmail")
print(f"Visit this URL to authenticate: {response['url']}")

# Start authentication flow for Slack with client ID
response = call_mcpauth_login(
    auth_server="slack"
)
```

**Supported Services**: Gmail, Google Calendar, Google Docs, Google Drive, Google Sheets, Slack, Notion, Linear, Asana, Outlook, OneDrive, Atlassian, Supabase, Airtable, Discord, and more.

## Configuration

### Environment Variables

```bash
# Option 1: API Key (Recommended)
export OBSERVEE_API_KEY="obs_your_key_here"
export OBSERVEE_CLIENT_ID="your_client_id"  # Optional

# Option 2: Direct URL
export OBSERVEE_URL="https://mcp.observee.ai/mcp"

# LLM Provider Keys
export ANTHROPIC_API_KEY="your_anthropic_key"
export OPENAI_API_KEY="your_openai_key" 
export GOOGLE_API_KEY="your_google_key"
```

### Function Parameters

```python
from observee_agents import chat_with_tools

result = chat_with_tools(
    message="Your query here",
    
    # Provider Configuration
    provider="anthropic",  # "anthropic", "openai", "gemini"
    model="claude-sonnet-4-20250514",  # Auto-detected if not provided
    
    # Authentication (priority: params > env vars)
    observee_api_key="obs_your_key",
    observee_url="https://custom.mcp.server/endpoint",
    client_id="your_client_id",
    
    # Tool Filtering
    enable_filtering=True,  # True for filtered tools, False for all tools
    filter_type="bm25",     # "bm25", "local_embedding", "cloud"
    max_tools=20,           # Maximum tools to filter
    min_score=8.0,          # Minimum relevance score
    
    # Performance
    sync_tools=False,       # True to clear caches and resync
    
    # 🆕 Conversation features
    session_id="my_assistant",  # Enable conversation memory
    system_prompt="You are a helpful expert...",  # Custom AI behavior
    
    # Provider-specific args
    temperature=0.7,
    max_tokens=1000
)
```

## Examples

## Available Imports

```python
# Main chat functionality
from observee_agents import chat_with_tools, chat_with_tools_stream

# Tool exploration and management
from observee_agents import list_tools, get_tool_info, filter_tools, execute_tool

# 🆕 Conversation management
from observee_agents import (
    get_conversation_history, 
    reset_conversation_history,
    list_sessions, 
    clear_session
)

# Advanced usage
from observee_agents import MCPAgent
```

### Multiple Providers

```python
from observee_agents import chat_with_tools

# Anthropic Claude
result = chat_with_tools(
    message="Analyze this YouTube video",
    provider="anthropic",
    model="claude-sonnet-4-20250514"
)

# OpenAI GPT
result = chat_with_tools(
    message="Search for recent AI papers", 
    provider="openai",
    model="gpt-4o"
)

# Google Gemini
result = chat_with_tools(
    message="Help me manage my emails",
    provider="gemini", 
    model="gemini-2.5-pro"
)
```

### 🆕 Specialized AI Assistants

```python
from observee_agents import chat_with_tools_stream

# Email management specialist
async for chunk in chat_with_tools_stream(
    message="Help me organize my inbox",
    session_id="email_bot",
    system_prompt="You are an email productivity expert. Focus on organization and efficiency.",
    provider="anthropic"
):
    # Handle streaming response...

# Data analysis specialist  
async for chunk in chat_with_tools_stream(
    message="Analyze the latest sales data",
    session_id="data_bot", 
    system_prompt="You are a data scientist. Provide technical insights and actionable recommendations.",
    provider="openai"
):
    # Handle streaming response...

# Content creation specialist
async for chunk in chat_with_tools_stream(
    message="Create a YouTube video summary",
    session_id="content_bot",
    system_prompt="You are a content strategist. Focus on engagement and storytelling.",
    provider="gemini"
):
    # Handle streaming response...
```

### Tool Filtering Options

```python
from observee_agents import chat_with_tools

# Fast BM25 keyword filtering (default)
result = chat_with_tools(
    message="Find relevant tools",
    filter_type="bm25",
    max_tools=5
)

# Semantic embedding filtering
result = chat_with_tools(
    message="Find relevant tools",
    filter_type="local_embedding",
    max_tools=10
)

# Cloud hybrid search (requires API keys)
result = chat_with_tools(
    message="Find relevant tools",
    filter_type="cloud",
    max_tools=15
)

# No filtering - use all available tools
result = chat_with_tools(
    message="What can you do?",
    enable_filtering=False
)
```

### Custom Configuration

```python
from observee_agents import chat_with_tools

# Custom Observee server
result = chat_with_tools(
    message="Custom server query",
    observee_url="https://your-custom-server.com/mcp",
    client_id="custom_client_123"
)

# Force cache refresh
result = chat_with_tools(
    message="Get fresh results", 
    sync_tools=True  # Clears caches
)
```

## Response Format

```python
{
    "content": "The AI response text",
    "tool_calls": [
        {
            "name": "tool_name",
            "input": {"param": "value"}
        }
    ],
    "tool_results": [
        {
            "tool": "tool_name", 
            "result": "tool output"
        }
    ],
    "filtered_tools_count": 5,
    "filtered_tools": ["tool1", "tool2", "tool3"],
    "used_filtering": True
}
```

## Available Tools

The SDK provides access to various MCP tools including:

- **📧 Gmail**: Email management, search, compose, labels
- **🎥 YouTube**: Video transcript retrieval and analysis  
- **📋 Linear**: Project management, issues, comments
- **🔍 Brave Search**: Web search and local business lookup
- **And many more...**

## Filter Types

### BM25 Filter (Default)
- **Speed**: ⚡ ~1-5ms per query
- **Best for**: Fast keyword matching, production use
- **Dependencies**: None (built-in)

### Local Embedding Filter  
- **Speed**: ⚡ ~10ms per query
- **Best for**: Semantic search without cloud dependencies
- **Dependencies**: `fastembed`

### Cloud Filter
- **Speed**: 🐌 ~300-400ms per query  
- **Best for**: Highest quality hybrid search
- **Dependencies**: `pinecone-client`, `openai`
- **Requirements**: `PINECONE_API_KEY`, `OPENAI_API_KEY`

## Development

```bash
# Clone and install in development mode
git clone https://github.com/observee-ai/mcp-agent-system.git #coming soon
cd mcp-agent-system
pip install -e .[dev]

# Run tests
pytest

# Format code
black observee_agents/
```

## License

All rights reserved. This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

## Support

- 📖 [Documentation](https://docs.observee.ai/mcp-agent-system)
- 🐛 [Issue Tracker](https://github.com/observee-ai/mcp-agent-system/issues)
- 💬 [Discord Community](https://discord.gg/jnf8yHWJ)
- 📧 [Email Support](mailto:contact@observee.ai) 