# Observee Auth Python SDK

OAuth authentication client for the Observee MCP Agent SDK, providing secure authentication flows for various services.

## Installation

```bash
pip install agents-oauth
```

## Quick Start

```python
from observee_auth import call_mcpauth_login

# Start OAuth flow for Gmail
response = call_mcpauth_login(auth_server="gmail")
print(f"Login URL: {response['auth_url']}")
```

## Features

- Simple OAuth authentication for multiple services
- Automatic environment variable configuration
- Support for 15+ authentication providers including Gmail, Slack, Notion, and more
- Client-specific server management
- Built-in error handling

## Configuration

Set your API key as an environment variable:

```bash
export OBSERVEE_API_KEY="your-api-key"
```

Or pass it directly:

```python
from observee_auth import McpAuthClient

client = McpAuthClient(api_key="your-api-key")
```

## Supported Services

- Google: Gmail, Calendar, Docs, Drive, Sheets, Slides
- Microsoft: Outlook, OneDrive, OneNote
- Productivity: Slack, Notion, Linear, Asana
- Development: Atlassian (Jira/Confluence), Supabase
- Other: Airtable, Discord

## Usage Examples

### List Available Servers

```python
from observee_auth import get_available_servers

servers = get_available_servers()
print(servers["supported_servers"])
```

### Start Authentication Flow

```python
from observee_auth import McpAuthClient

client = McpAuthClient()

# Start Slack OAuth
response = client.start_auth_flow("slack")
auth_url = response["auth_url"]

# With additional parameters
response = client.start_auth_flow(
    "atlassian",
    additional_params={"workspace": "my-workspace"}
)
```

### Get Client-Specific Servers

```python
from observee_auth import get_servers_by_client

servers = get_servers_by_client("my-client-id")
print(f"Total servers: {servers['total_count']}")
```

## API Reference

### McpAuthClient

Main client class for interacting with the mcpauth API.

#### Methods

- `get_available_servers()`: Get all available authentication servers
- `start_auth_flow(auth_server, client_id=None, additional_params=None)`: Start an OAuth flow
- `list_supported_servers()`: Get a simple list of supported server names
- `get_servers_by_client(client_id)`: Get servers associated with a client ID

### Convenience Functions

- `call_mcpauth_login(api_key=None, auth_server="gmail", client_id=None, additional_params=None)`
- `get_available_servers(api_key=None)`
- `get_servers_by_client(client_id, api_key=None)`

## Error Handling

```python
from observee_auth import McpAuthError

try:
    response = call_mcpauth_login(auth_server="invalid")
except McpAuthError as e:
    print(f"Authentication error: {e}")
```

## License

MIT License - see LICENSE file for details.