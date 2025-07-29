# Observee Auth

A TypeScript SDK for seamless OAuth authentication with popular services including Gmail, Slack, Notion, and 15+ other platforms. Simplify your authentication workflows with built-in OAuth flows and secure token management.

**Configure and manage OAuth for any supported service at [observee.ai](https://observee.ai)**

## Installation

```bash
# Basic installation
npm install @observee/auth
```

## Quick Start

## API Key Configuration

### Environment Variable (Recommended)

Set your Observee API key as an environment variable:

```bash
export OBSERVEE_API_KEY="your_api_key_here"
```

When the environment variable is set, you can call functions without passing the API key:

```typescript
import { callMcpAuthLogin, getAvailableServers } from "@observee/auth";

// No need to pass apiKey when environment variable is set
const servers = await getAvailableServers();
console.log(`Available servers: ${servers.supported_servers}`);

const response = await callMcpAuthLogin({
  authServer: "gmail",
});
console.log(`Visit this URL to authenticate: ${response.url}`);
```

### Direct Parameter Passing

If you prefer not to use environment variables, you can pass the API key directly to functions:

```typescript
import { callMcpAuthLogin, getAvailableServers } from "@observee/auth";

const API_KEY = "your_api_key_here";

// Pass apiKey as parameter
const servers = await getAvailableServers(API_KEY);
console.log(`Available servers: ${servers.supported_servers}`);

const response = await callMcpAuthLogin({
  authServer: "gmail",
  apiKey: API_KEY,
});
console.log(`Visit this URL to authenticate: ${response.url}`);
```

**Note**: The API key passed as a parameter takes precedence over the environment variable.

## Authentication Flow Details

### Using a Custom Redirect URL

If you provide a `customRedirectUrl` when calling `callMcpAuthLogin`, after the user completes authentication, they will be redirected to your specified URL. The redirect will include both `client_id` and `customer_id` as query parameters in the URL. This allows your application to capture these identifiers directly from the callback request and handle them as needed.

### Default Flow (No Custom Redirect URL)

If you do not specify a `customRedirectUrl`, the user will complete authentication at the default Observee endpoint. After authentication, the flow will return a JSON response containing:

- `customer_id`: Represents you, the authenticated user.
- `client_id`: The client you authenticated with.

You can use these values in your application to identify the user and the client associated with the authentication session.

**Supported Services**: Gmail, Google Calendar, Google Docs, Google Drive, Google Sheets, Slack, Notion, Linear, Asana, Outlook, OneDrive, Atlassian, Supabase, Airtable, Discord, and more.
