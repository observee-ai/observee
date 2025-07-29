# Observee SDK Logger

The Observee SDK Logger provides automatic logging capabilities for MCP (Model Context Protocol) servers, allowing you to track tool and prompt usage.

## Installation

You can install the Observee packages in different ways:

````bash
# Option 1: Individual package
npm install @observee/logger

# Option 2: Full SDK (includes all packages)
npm install @observee/sdk


## Import Options

The Observee logger supports multiple import patterns:

```typescript
// Option 1: Main package export
import { Logger, observeeUsageLogger } from "@observee/logger";

// Option 2: From full SDK
import { Logger, observeeUsageLogger } from "@observee/sdk";


## Basic Usage

At the top of your MCP server file, import the logger components:

```typescript
import { Logger, observeeUsageLogger } from "@observee/logger";
````

Create a logger instance with your MCP server name:

```typescript
const logger = new Logger("your-server-name", {
  apiKey: "your-api-key",
});
```

Wrap your request handlers with the usage logger:

```typescript
// For tool calls
server.setRequestHandler(
  CallToolRequestSchema,
  observeeUsageLogger(logger, async (request) => {
    // your tool handler code here
  })
);

// For prompt calls
server.setRequestHandler(
  GetPromptRequestSchema,
  observeeUsageLogger(logger, async (request) => {
    // your prompt handler code here
  })
);
```

## Configuration Options

The Logger constructor accepts two parameters:

1. **mcpServerName** (required): A string identifier for your MCP server
2. **config** (optional): Configuration object with the following options:

### API Key vs Log File (Mutually Exclusive)

You can configure the logger to use either API logging or file logging, but not both:

#### API Logging

When `apiKey` is provided, logs are sent to the Observee API:

```typescript
const logger = new Logger("my-server", {
  apiKey: "your-api-key",
});
```

#### File Logging

When `logFile` is provided with a filename, logs are written to that file in the system logs directory:

```typescript
const logger = new Logger("my-server", {
  logFile: "my-server.log", // Creates file in system logs directory
});
```

**System Log Directories:**

- **macOS**: `~/Library/Logs/observee/my-server.log`
- **Linux**: `~/.cache/observee/my-server.log`
- **Windows**: `%LOCALAPPDATA%/observee/my-server.log`

The logger will automatically create the `observee` directory if it doesn't exist.

**Fallback Behavior**: If API logging fails, the logger will automatically fall back to file logging (if configured) as a backup.

## Complete Example

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  GetPromptRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Logger, observeeUsageLogger } from "@observee/logger";

const server = new Server(
  {
    name: "my-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      prompts: {},
    },
  }
);

// Initialize the logger
const logger = new Logger("my-mcp-server", {
  apiKey: process.env.OBSERVEE_API_KEY,
  logFile: "my-mcp-server.log", // Optional: fallback to file logging
});

// Wrap your tool call handler
server.setRequestHandler(
  CallToolRequestSchema,
  observeeUsageLogger(logger, async (request) => {
    const { name, arguments: args } = request.params;

    switch (name) {
      case "my-tool":
        // Your tool implementation
        return {
          content: [
            {
              type: "text",
              text: "Tool result",
            },
          ],
        };
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  })
);

// Wrap your prompt handler
server.setRequestHandler(
  GetPromptRequestSchema,
  observeeUsageLogger(logger, async (request) => {
    const { name, arguments: args } = request.params;

    switch (name) {
      case "my-prompt":
        // Your prompt implementation
        return {
          description: "A sample prompt",
          messages: [
            {
              role: "user",
              content: {
                type: "text",
                text: "This is a sample prompt response",
              },
            },
          ],
        };
      default:
        throw new Error(`Unknown prompt: ${name}`);
    }
  })
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main();
```

## Tool and Prompt Logging

The logger automatically handles both tool calls and prompt requests:

### Tool Logging

When a tool is called via the `tools/call` method, the logger captures:

- Tool name
- Input parameters (with sensitive parameters like `server_session_id` automatically filtered)
- Tool response
- Execution duration
- Session ID (if provided)

### Prompt Logging

When a prompt is requested via the `prompts/get` method, the logger captures:

- Prompt name
- Input parameters (with sensitive parameters automatically filtered)
- Prompt response (description and messages)
- Session ID (if provided)

Both types of requests are automatically detected and logged with appropriate metadata.

## What Gets Logged

The logger automatically captures detailed information for all MCP requests:

- **Successful Operations**: Complete request/response data with execution metrics
- **Error Cases**: Failed operations with error messages and timing information
- **Session Context**: Automatic session ID extraction and tracking
- **Performance Metrics**: Request duration and timing data

## Session Tracking

The logger automatically extracts and handles `server_session_id` parameters from both tool calls and prompt requests for session tracking, while removing them from the logged input to keep logs clean. This allows you to track related operations across a user session without cluttering your logs.

## Error Handling

If logging fails (network issues, invalid API key, etc.), the error is logged to console but doesn't interrupt your MCP server's operation.

## Advanced Usage

### Modular Architecture

The logger is built with a modular architecture that allows you to import specific components:

```typescript
// Import specific components (clean submodule imports)
import { Logger } from "@observee/logger/logger";
import { observeeUsageLogger } from "@observee/logger/middleware";
import { getLogsDirectory, createLogFilePath } from "@observee/logger/utils";
import type { ToolUsageData, PromptUsageData } from "@observee/logger/types";
```

### Working with Log File Paths

You can work with log file paths using the utility functions:

```typescript
import { createLogFilePath, getLogsDirectory } from "@observee/logger";

// Get the system logs directory
const logsDir = getLogsDirectory();
console.log(`Logs directory: ${logsDir}`);

// Create a log file path for a specific filename
const logPath = createLogFilePath("my-server.log");
console.log(`Full path: ${logPath}`);

const logger = new Logger("my-server", {
  logFile: "my-server.log",
});
```

### Accessing Log File Path

You can retrieve the current log file path from the logger:

```typescript
const logger = new Logger("my-server", { logFile: "my-server.log" });
const logPath = logger.getLogFilePath();
console.log(`Logging to: ${logPath}`);
```
