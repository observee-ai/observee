[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/observee-ai-observee-badge.png)](https://mseep.ai/app/observee-ai-observee)

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./public/images/observee_white.png">
    <source media="(prefers-color-scheme: light)" srcset="./public/images/observee_large.png">
    <img src="./public/images/observee_white.png" width="80%" style="margin: 20px auto;" alt="Observee Logo">
  </picture>
</div>


<p align="center">
  <a href="https://observee.ai">🌐 Website</a>  | 
  <a href="https://docs.observee.ai">📚 Docs</a>  | 
  <a href="https://discord.com/invite/QCgXDSCNC6">💬 Discord</a>  | 
  <a href="https://www.linkedin.com/company/observee">💼 LinkedIn</a>  | 
  <a href="https://x.com/observeeinc">𝕏</a>
</p>

<p align="center">
  ⭐ If you like Observee, <a href="https://github.com/observee-ai/observee">please star us on GitHub!</a>
</p>

# Observee SDK

**The complete Observee SDK - All-in-one package for using MCPs with AI agents, authentication management for MCPs, and complete observability for MCP Builders.**

Available for both **TypeScript/JavaScript** and **Python**.

## What's Included

This SDK includes all Observee components:

- 🤖 **Agents** - MCP tool integration with LLM providers ([npm](https://www.npmjs.com/package/@observee/agents) | [pypi](https://pypi.org/project/mcp-agents/))
- 🔐 **Auth** - OAuth authentication for 15+ services ([npm](https://www.npmjs.com/package/@observee/auth) | [pypi](https://pypi.org/project/agents-oauth/))
- 📊 **Logger** - Structured logging and monitoring ([npm](https://www.npmjs.com/package/@observee/logger) | [pypi](https://pypi.org/project/mcp-logger/))

## Quick Start

### TypeScript/JavaScript

```bash
# Install everything at once
npm install @observee/sdk

# Or install individual packages
npm install @observee/agents @observee/auth @observee/logger
```

### Python

```bash
# Install individual packages (no meta-package yet)
pip install mcp-agents agent-oauth mcp-logger

# Or install all at once
pip install observee
```

### Usage Examples

#### TypeScript/JavaScript

**Option 1: Import from main package**

```typescript
import { chatWithTools, callMcpAuthLogin, Logger } from "@observee/sdk";

// Use agents
const result = await chatWithTools("Search for news", {
  provider: "anthropic",
  observeeApiKey: "obs_your_key",
});

// Use auth
const authResponse = await callMcpAuthLogin({
  authServer: "gmail",
});

// Use logger
const logger = new Logger({ apiKey: "obs_your_key" });
logger.info("Application started");
```

**Option 2: Import from specific sub-packages**

```typescript
import { chatWithTools } from "@observee/agents";
import { callMcpAuthLogin } from "@observee/auth";
import { Logger } from "@observee/logger";
```

#### Python

```python
from observee_agents import chat_with_tools
from observee_auth import call_mcpauth_login

# Use agents
result = chat_with_tools(
    "Search for news",
    provider="anthropic",
    observee_api_key="obs_your_key"
)

# Use auth
auth_response = call_mcpauth_login(auth_server="gmail")
print(f"Login URL: {auth_response['auth_url']}")

```

## Complete Example

### TypeScript/JavaScript

```typescript
import { chatWithTools, callMcpAuthLogin, Logger } from "@observee/sdk";

// Set up logging
const logger = new Logger({
  apiKey: "obs_your_key",
  service: "my-app",
});

async function main() {
  try {
    // Authenticate with Gmail
    logger.info("Starting Gmail authentication");
    const auth = await callMcpAuthLogin({
      authServer: "gmail",
    });
    console.log("Visit:", auth.url);

    // Use AI agent with tools
    logger.info("Starting AI chat with tools");
    const result = await chatWithTools("Search my emails for project updates", {
      provider: "anthropic",
      observeeApiKey: "obs_your_key",
    });

    console.log("AI Response:", result.content);
    logger.info("AI chat completed", {
      toolsUsed: result.toolCalls?.length || 0,
    });
  } catch (error) {
    logger.error("Application error", { error: error.message });
  }
}

main();
```

### Python

```python
from observee_agents import chat_with_tools call_mcpauth_login
import asyncio


async def main():
    try:
        # Authenticate with Gmail
        logger.info("Starting Gmail authentication")
        auth = call_mcpauth_login(auth_server="gmail")
        print(f"Visit: {auth['auth_url']}")

        # Use AI agent with tools
        logger.info("Starting AI chat with tools")
        result = await chat_with_tools(
            "Search my emails for project updates",
            provider="anthropic",
            observee_api_key="obs_your_key"
        )

        print(f"AI Response: {result['content']}")
    except Exception as error:
        logger.error("Application error", {"error": str(error)})

# Run the async function
asyncio.run(main())
```

## Features Overview

### 🤖 AI Agents

- **Multi-Provider Support**: Anthropic Claude, OpenAI GPT, Google Gemini
- **MCP Tool Integration**: 15+ pre-built tools (Gmail, YouTube, Linear, etc.)
- **Smart Filtering**: BM25, local embeddings, cloud-based filtering
- **Streaming Support**: Real-time responses
- **Conversation Memory**: Persistent chat history

### 🔐 Authentication

- **OAuth 2.0 Flows**: Gmail, Slack, Notion, Linear, GitHub, and more
- **Simple Integration**: One-line authentication
- **Secure Token Management**: Automatic storage and refresh
- **Custom Redirects**: Support for self-hosted servers

### 📊 Logging

- **Structured Logging**: JSON-based log format
- **Usage Tracking**: Monitor API usage and costs
- **Multiple Transports**: Console, file, and cloud logging
- **Performance Monitoring**: Track response times and errors

## Support

- 📖 [Documentation](https://docs.observee.ai)
- 🐛 [Issue Tracker](https://github.com/observee-ai/observee/issues)
- 💬 [Discord Community](https://discord.com/invite/QCgXDSCNC6)
- 📧 [Email Support](mailto:founders@observee.ai)

## Citation

If you use Observee in your research or project, please cite:

```bibtex
@software{observee,
  title={Observee},
  author={observee-ai},
  year={2025},
  publisher = {GitHub},
  url={https://github.com/observee-ai/observee}
}
```
