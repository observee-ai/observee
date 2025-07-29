# Observee Agents

A TypeScript SDK for seamless integration of MCP (Model Context Protocol) tools with multiple LLM providers including Anthropic Claude, OpenAI GPT, and Google Gemini.

**Configure as many MCP servers/tools as you need at [observee.ai](https://observee.ai)**

## Features

- 🤖 **Multi-Provider Support**: Works with Anthropic, OpenAI, and Gemini
- 🔧 **Smart Tool Filtering**: BM25, local embeddings, and cloud-based filtering
- ⚡ **Fast Performance**: Intelligent caching and optimization
- 🔑 **Flexible Authentication**: URL-based or API key authentication
- 🔐 **OAuth Integration**: Built-in authentication flows for Gmail, Slack, Notion, and 15+ services
- 🎯 **Easy Integration**: Simple async API
- 📡 **Streaming Support**: Real-time streaming responses for Anthropic, OpenAI, and Gemini
- 🗨️ **Conversation History**: Persistent memory across chat sessions
- 🎯 **Custom System Prompts**: Personalized AI behavior and expertise
- 📦 **NPM Installable**: Easy installation and distribution

## Installation

```bash
# Basic installation
npm install @observee/agents

# Development installation
git clone https://github.com/observee-ai/agents-ts.git
cd agents-ts
npm install
npm run build
```

## API Key Configuration

### Environment Variables (Recommended)

Set your Observee API key as an environment variable:

```bash
# Option 1: API Key + Client ID (Recommended)
export OBSERVEE_API_KEY="obs_your_key_here"
export OBSERVEE_CLIENT_ID="your_client_id"  # Required when using API key

# Option 2: Direct URL (Alternative)
export OBSERVEE_URL="https://mcp.observee.ai/mcp"

# LLM Provider Keys
export ANTHROPIC_API_KEY="your_anthropic_key"
export OPENAI_API_KEY="your_openai_key"
export GOOGLE_API_KEY="your_google_key"
```

You can retrieve your `OBSERVEE_URL` from the "Get Config" button in the `app.observee.ai` in `Connect`.

When environment variables are set, you can use `chatWithTools` without passing authentication parameters:

```typescript
// Uses OBSERVEE_API_KEY and OBSERVEE_CLIENT_ID environment variables
const result = await chatWithTools("Search for news", {
  provider: "anthropic",
  model: "claude-3-5-sonnet-20241022",
});
```

### Direct Parameter Passing

Alternatively, you can pass authentication parameters directly to `chatWithTools`:

**Option 1: API Key + Client ID**

```typescript
const result = await chatWithTools("Search for news", {
  provider: "anthropic",
  observeeApiKey: "obs_your_key_here",
  clientId: "your_client_id", // Required when using observeeApiKey
});
```

**Option 2: Direct URL**

```typescript
const result = await chatWithTools("Search for news", {
  provider: "anthropic",
  observeeUrl: "https://custom.mcp.server/endpoint", // Alternative to API key
});
```

**Important**:

- If you pass `observeeApiKey`, you **must** also pass `clientId`
- If you don't have an API key, you can use `observeeUrl` instead
- Parameters passed directly take precedence over environment variables

## Configuration

```typescript
import { chatWithTools } from "@observee/agents";

const result = await chatWithTools("Your query here", {
  // Provider Configuration
  provider: "anthropic", // "anthropic", "openai", "gemini"
  model: "claude-3-5-sonnet-20241022", // Auto-detected if not provided

  // Authentication (priority: params > env vars)
  observeeApiKey: "obs_your_key",
  observeeUrl: "https://custom.mcp.server/endpoint",
  clientId: "your_client_id",

  // Tool Filtering
  enableFiltering: true, // true for filtered tools, false for all tools
  filterType: "bm25", // "bm25", "local_embedding", "cloud"
  maxTools: 20, // Maximum tools to filter
  minScore: 8.0, // Minimum relevance score

  // Performance
  syncTools: false, // true to clear caches and resync

  // Provider-specific args
  temperature: 0.7,
  max_tokens: 1000,
});
```

### Custom Tools

You can extend the SDK with your own custom tools by creating them in OpenAI function format and handling execution:

```typescript
import { MCPAgent } from "@observee/agents";

// Create agent with custom tools support
const agent = new MCPAgent({
  provider: "openai",
  serverUrl: "https://mcp.observee.ai/mcp",
  observeeApiKey: "obs_your_key_here",
});

await agent.initialize();

// Add custom tool execution logic
const originalExecuteTool = agent.executeTool.bind(agent);
agent.executeTool = async function (toolName: string, input: any) {
  // Handle custom tools
  if (toolName === "add_numbers") {
    return String((input.a || 0) + (input.b || 0));
  } else if (toolName === "get_time") {
    return new Date().toLocaleTimeString();
  } else {
    // Fallback to original MCP tools
    return originalExecuteTool(toolName, input);
  }
};

// Custom tools work seamlessly with all providers and can be combined with MCP tools
const result = await agent.chatWithTools(
  "What's 5 + 3? Also, what time is it?"
);
console.log(result.content);

await agent.close();
```

Custom tools work seamlessly with all providers (Anthropic, OpenAI, Gemini) and can be combined with MCP tools for enhanced functionality.

### Streaming Responses

```typescript
import { chatWithToolsStream } from "@observee/agents";

for await (const chunk of chatWithToolsStream(
  "What's the weather like today?",
  {
    provider: "openai",
    observeeApiKey: "obs_your_key_here",
  }
)) {
  if (chunk.type === "content") {
    process.stdout.write(chunk.content || "");
  } else if (chunk.type === "tool_result") {
    console.log(`\n[Tool executed: ${chunk.toolName}]`);
  }
}
```

### 🆕 Conversational AI with Memory

```typescript
import { MCPAgent } from "@observee/agents";

// Create a specialized assistant with conversation memory
const agent = new MCPAgent({
  provider: "anthropic",
  serverUrl: "https://mcp.observee.ai/mcp",
  observeeApiKey: "obs_your_key_here",
});

await agent.initialize();

// First message
const result1 = await agent.chatWithTools("Search for emails about meetings");
console.log(result1.content);

console.log("\n" + "=" * 40 + "\n");

// Follow-up - remembers previous context!
const result2 = await agent.chatWithTools(
  "What was the subject of the first meeting?"
);
console.log(result2.content);

// Check conversation history
const history = agent.getConversationHistory();
console.log(`\n📊 Conversation has ${history.length} messages`);

await agent.close();
```

### Advanced Async Usage

```typescript
import { MCPAgent } from "@observee/agents";

const agent = new MCPAgent({
  provider: "anthropic",
  serverUrl: "wss://mcp.observee.ai/mcp?client_id=your_id",
  authToken: "obs_your_key_here",
});

try {
  await agent.initialize();
  const result = await agent.chatWithTools("What tools do you have access to?");
  console.log(result.content);
} finally {
  await agent.close();
}
```

## Examples

## Available Imports

```typescript
// Main chat functionality
import { chatWithTools, chatWithToolsStream } from "@observee/agents";

// OAuth authentication
import {
  callMcpAuthLogin,
  getAvailableServers,
  McpAuthClient,
} from "@observee/agents";

// Advanced usage
import { MCPAgent } from "@observee/agents";

// Types
import type {
  ChatWithToolsResponse,
  StreamChunk,
  ToolCall,
  ToolResult,
  AgentConfig,
} from "@observee/agents";
```

### Multiple Providers

```typescript
import { chatWithTools } from "@observee/agents";

// Anthropic Claude
const result1 = await chatWithTools("Analyze this YouTube video", {
  provider: "anthropic",
  model: "claude-3-5-sonnet-20241022",
});

// OpenAI GPT
const result2 = await chatWithTools("Search for recent AI papers", {
  provider: "openai",
  model: "gpt-4o",
});

// Google Gemini
const result3 = await chatWithTools("Help me manage my emails", {
  provider: "gemini",
  model: "gemini-2.0-flash-exp",
});
```

### 🆕 Specialized AI Assistants

```typescript
import { MCPAgent } from "@observee/agents";

// Email management specialist
const emailBot = new MCPAgent({
  provider: "anthropic",
  serverUrl: "https://mcp.observee.ai/mcp",
  observeeApiKey: "obs_your_key_here",
});

await emailBot.initialize();
const emailResult = await emailBot.chatWithTools("Help me organize my inbox");
console.log(emailResult.content);

// Data analysis specialist
const dataBot = new MCPAgent({
  provider: "openai",
  serverUrl: "https://mcp.observee.ai/mcp",
  observeeApiKey: "obs_your_key_here",
});

await dataBot.initialize();
const dataResult = await dataBot.chatWithTools("Analyze the latest sales data");
console.log(dataResult.content);

// Clean up
await emailBot.close();
await dataBot.close();
```

### Tool Filtering Options

```typescript
import { chatWithTools } from "@observee/agents";

// Fast BM25 keyword filtering (default)
const result1 = await chatWithTools("Find relevant tools", {
  filterType: "bm25",
  maxTools: 5,
});

// Semantic embedding filtering (coming soon)
const result2 = await chatWithTools("Find relevant tools", {
  filterType: "local_embedding",
  maxTools: 10,
});

// Cloud hybrid search (requires API keys)
const result3 = await chatWithTools("Find relevant tools", {
  filterType: "cloud",
  maxTools: 15,
});

// No filtering - use all available tools
const result4 = await chatWithTools("What can you do?", {
  enableFiltering: false,
});
```

### Custom Configuration

```typescript
import { chatWithTools } from "@observee/agents";

// Custom Observee server
const result1 = await chatWithTools("Custom server query", {
  observeeUrl: "https://your-custom-server.com/mcp",
  clientId: "custom_client_123",
});

// Force cache refresh
const result2 = await chatWithTools("Get fresh results", {
  syncTools: true, // Clears caches
});
```

## Response Format

```typescript
interface ChatWithToolsResponse {
  content: string; // The AI response text
  toolCalls?: ToolCall[]; // List of tool calls made
  toolResults?: ToolResult[]; // Results from tool executions
  filteredToolsCount: number; // Number of tools after filtering
  filteredTools: string[]; // List of filtered tool names
  usedFiltering: boolean; // Whether filtering was used
  initialResponse?: string; // Initial response before tool execution
}

interface ToolCall {
  name: string; // Tool name
  input: Record<string, any>; // Tool input parameters
}

interface ToolResult {
  tool: string; // Tool name
  result?: string; // Tool output
  error?: string; // Error message if failed
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
- **Dependencies**: `@xenova/transformers`

### Cloud Filter

- **Speed**: 🐌 ~300-400ms per query
- **Best for**: Highest quality hybrid search
- **Dependencies**: `@pinecone-database/pinecone`, `openai`
- **Requirements**: `PINECONE_API_KEY`, `OPENAI_API_KEY`

## Streaming Support

Real-time streaming capabilities allow you to receive responses as they're generated, providing immediate feedback to users.

**Two Ways to Stream:**

1. **High-level function**: `chatWithToolsStream()` - Easy to use, handles agent lifecycle automatically
2. **Agent methods**: `agent.chatStream()` and `agent.chatWithToolsStream()` - More control over agent configuration

**Important:** Use `chatWithToolsStream()` (with "Stream") for actual streaming. The method `chatWithToolsStreaming()` (with "Streaming") is NOT streaming - it returns a Promise.

### High-Level Streaming Function

Use the `chatWithToolsStream()` function for easy streaming without managing agent lifecycle:

```typescript
import { chatWithToolsStream } from "@observee/agents";

// Complete 3-phase streaming workflow with automatic cleanup
for await (const chunk of chatWithToolsStream("Search for AI news", {
  provider: "anthropic",
  enableFiltering: true,
  maxTools: 10,
})) {
  switch (chunk.type) {
    case "phase":
      console.log(`\n🎯 Phase: ${chunk.phase}`);
      break;
    case "content":
      process.stdout.write(chunk.content || "");
      break;
    case "tool_call":
      console.log(`\n🔧 Calling: ${chunk.toolCall?.name}`);
      break;
    case "tool_result":
      console.log(`\n✅ Tool executed: ${chunk.toolName}`);
      break;
    case "final_content":
      process.stdout.write(chunk.content || "");
      break;
    case "done":
      console.log(`\n✅ Stream complete!`);
      break;
  }
}
```

### Agent-Level Streaming

For more control over the agent lifecycle, use the `MCPAgent` class methods:

#### Basic Streaming

Use `agent.chatStream()` for simple streaming responses with tool filtering:

```typescript
import { MCPAgent } from "@observee/agents";

const agent = new MCPAgent({
  provider: "anthropic",
  serverUrl: "https://mcp.observee.ai/mcp",
  enableFiltering: true,
});

await agent.initialize();

// Stream basic responses
for await (const chunk of agent.chatStream("What's the weather today?")) {
  if (chunk.type === "content") {
    process.stdout.write(chunk.content || "");
  } else if (chunk.type === "tool_call") {
    console.log(`\n🔧 Tool: ${chunk.toolCall?.name}`);
  }
}

await agent.close();
```

#### Complete Streaming Workflow

Use `agent.chatWithToolsStream()` for the full 3-phase streaming workflow:

```typescript
import { MCPAgent } from "@observee/agents";

const agent = new MCPAgent({
  provider: "openai",
  model: "gpt-4o",
  serverUrl: "https://mcp.observee.ai/mcp",
  enableFiltering: true,
});

await agent.initialize();

for await (const chunk of agent.chatWithToolsStream(
  "Analyze recent AI papers",
  10,
  8.0
)) {
  switch (chunk.type) {
    case "phase":
      console.log(`\n📍 ${chunk.phase}`);
      break;
    case "content":
      process.stdout.write(chunk.content || "");
      break;
    case "tool_call":
      console.log(`\n🔧 ${chunk.toolCall?.name}`);
      break;
    case "tool_result":
      console.log(`\n✅ ${chunk.toolName}: ${chunk.result?.slice(0, 100)}...`);
      break;
    case "final_content":
      process.stdout.write(chunk.content || "");
      break;
    case "done":
      console.log("\n✅ Complete!");
      break;
  }
}

await agent.close();
```

### StreamChunk Types

- **`content`**: Streaming response content chunks
- **`tool_call`**: Tool being called with parameters
- **`metadata`**: Final metadata with tool counts and filtering info (only in `chatStream`)
- **`phase`**: Workflow phase changes - "initial_response", "tool_execution", "final_response" (only in `chatWithToolsStream`)
- **`tool_result`**: Successful results from tool execution (only in `chatWithToolsStream`)
- **`tool_error`**: Errors that occurred during tool execution (only in `chatWithToolsStream`)
- **`final_content`**: Final response content after tool execution (only in `chatWithToolsStream`)
- **`done`**: Stream completion with final metadata

### Streaming Workflow Phases

The `chatWithToolsStream()` method follows a three-phase workflow:

1. **Initial Response Phase**: AI generates response and identifies needed tools
2. **Tool Execution Phase**: Tools are called and results are gathered
3. **Final Response Phase**: AI generates final response incorporating tool results

### Running the Streaming Example

```bash
# Install and build
npm install && npm run build

# Run streaming example
npm run example:quick
```

## API Reference

### `chatWithTools(message, options)`

Main function for chatting with tool support.

**Parameters:**

- `message` (string): The user query
- `options` (object):
  - `provider` (string): LLM provider - "anthropic", "openai", "gemini" (default: "anthropic")
  - `model` (string): Model name (optional, uses provider defaults)
  - `observeeUrl` (string): Direct Observee MCP server URL
  - `observeeApiKey` (string): Observee API key for authentication
  - `clientId` (string): Observee client ID
  - `maxTools` (number): Maximum tools to filter (default: 20)
  - `minScore` (number): Minimum relevance score (default: 8.0)
  - `filterType` (string): Filter type - "bm25" (default: "bm25")
  - `enableFiltering` (boolean): Enable tool filtering (default: true)
  - `syncTools` (boolean): Clear caches and sync tools (default: false)

**Returns:** `ChatWithToolsResponse` with:

- `content`: The response text
- `toolCalls`: List of tool calls made
- `toolResults`: Results from tool executions
- `filteredToolsCount`: Number of tools after filtering
- `filteredTools`: List of filtered tool names
- `usedFiltering`: Whether filtering was used

### `chatWithToolsStream(message, options)`

High-level function for streaming chat with tools - handles agent lifecycle automatically.

**Parameters:** Same as `chatWithTools()`

**Returns:** `AsyncGenerator<StreamChunk>` - Stream of response chunks

**Usage:**

```typescript
for await (const chunk of chatWithToolsStream("Search for news", options)) {
  // Handle streaming chunks
}
```

### `MCPAgent` Class

Lower-level agent class for more control.

**Methods:**

- `constructor(config)`: Create new agent instance
- `initialize()`: Connect to MCP server and load tools
- `chat(message, maxTools, minScore)`: Get response with tool calls
- `executeTool(name, input)`: Execute a specific tool
- `chatWithTools(message, maxTools, minScore)`: Complete flow with tool execution
- `chatStream(message, maxTools, minScore)`: Stream responses with filtered tools
- `chatWithToolsStream(message, maxTools, minScore)`: Stream complete workflow with tool execution
- `resetConversation()`: Clear conversation history
- `getConversationHistory()`: Get message history
- `close()`: Clean up connections

**Streaming Methods:**

- `chatStream(message, maxTools?, minScore?)`: Returns an async generator that yields `StreamChunk` objects for basic streaming with tool calls but no automatic execution
- `chatWithToolsStream(message, maxTools?, minScore?)`: Returns an async generator for the complete 3-phase workflow with automatic tool execution:
  1. **Initial response phase**: AI generates response and identifies needed tools
  2. **Tool execution phase**: Tools are automatically called and results gathered
  3. **Final response phase**: AI generates final response incorporating tool results

**StreamChunk Interface:**

```typescript
interface StreamChunk {
  type:
    | "content"
    | "tool_call"
    | "metadata"
    | "phase"
    | "tool_result"
    | "tool_error"
    | "final_content"
    | "done";
  content?: string;
  toolCall?: ToolCall;
  toolName?: string;
  result?: string;
  error?: string;
  phase?: string;
  filteredToolsCount?: number;
  filteredTools?: string[];
  usedFiltering?: boolean;
  toolCalls?: ToolCall[];
  finalResponse?: ChatWithToolsResponse;
}

interface ToolCall {
  name: string;
  input: Record<string, any>;
}
```

## Development

```bash
# Clone and install in development mode
git clone https://github.com/observee-ai/agents-ts.git
cd agents-ts
npm install

# Build
npm run build

# Watch mode for development
npm run dev

# Run tests
npm test

# Run examples
npm run example:quick
npm run example:simple

# Lint code
npm run lint
npm run lint:fix
```

## License

All rights reserved. This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

## Support

- 📖 [Documentation](https://docs.observee.ai)
- 🐛 [Issue Tracker](https://github.com/observee-ai/observee/issues)
- 💬 [Discord Community](https://discord.gg/jnf8yHWJ)
- 📧 [Email Support](mailto:contact@observee.ai)
