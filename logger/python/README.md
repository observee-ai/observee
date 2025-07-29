# Observe Python SDK

A Python SDK for MCP tool and prompt usage logging and monitoring.

## Installation

```bash
pip install observee
```

## Usage

You can set the MCP server name either globally or per decorator:

### Global Configuration

```python
from observee import ObserveeConfig, observee_usage_logger

# Set the MCP server name globally
ObserveeConfig.set_mcp_server_name("your-mcp-server-name")

# Auto-detection based on function name
@observee_usage_logger
async def your_tool_function():
    # Your tool code here
    pass

@observee_usage_logger
async def generate_prompt():
    # Your prompt code here - auto-detected as prompt
    pass
```

### API Key Configuration (Developers and Enterprise Customers)

```python
from observee import ObserveeConfig

# Set your API key
ObserveeConfig.set_api_key("your-api-key")
```

### Unified Usage Logging

```python
from observee import ObserveeConfig, observee_usage_logger

# Auto-detection based on function name (recommended)
@observee_usage_logger()
async def your_tool_function():
    # Your tool code here
    pass

@observee_usage_logger()
async def generate_prompt():
    # Your prompt code here
    pass

```

## Features

- **Unified decorator** for both tool and prompt usage logging with async support
- **Auto-detection** of usage type based on function names (or explicit specification)
- Automatic logging of:
  - Tool/prompt name
  - Input parameters
  - Response data
  - Execution duration (for tools only)
  - Error information (if any)
- Configurable logging endpoint (defaults to Observe API)
- Error handling and reporting
- Performance tracking (for tools only)
- Flexible MCP server name configuration
- API key support for enhanced features
- Privacy protection: Input/response data only logged when API key is provided


## Logging Details

### Unified Usage Logging

The SDK uses a single `@observee_usage_logger()` decorator that can automatically detect whether you're logging a tool or prompt based on the function name, or you can specify explicitly:

**Auto-detection**: Functions containing keywords like 'prompt', 'template', or 'message' in their name are detected as prompts. All others are treated as tools.

**Tool logging** includes:
- MCP server name
- Tool name (derived from function name)
- Tool input parameters (as JSON)
- Tool response
- Execution duration in milliseconds
- Any errors that occur during execution

**Prompt logging** includes:
- MCP server name
- Prompt name (derived from function name)  
- Prompt input parameters (as JSON)
- Prompt response
- Any errors that occur during execution



### Privacy Protection

For privacy protection, detailed input and response data is only logged when an API key is configured. Without an API key, only basic metadata is logged:
- For tools: server name, tool name, and execution duration
- For prompts: server name and prompt name

Logs are sent asynchronously to avoid impacting tool/prompt performance.

## Requirements

- Python 3.8 or higher
- Dependencies:
  - httpx
  - pydantic

## License

GPL v3 - see [LICENSE](LICENSE) file for details 